from __future__ import annotations

import json
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.models.task import Task, TaskStatus, task_store
from app.tasks.worker import process_task, publish_progress

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
IDEMPOTENCY_KEY_PREFIX = "task:idempotency:"


def serialize_task(task: Task) -> dict:
    return {
        "id": task.id,
        "status": task.status.value,
        "processor_name": task.processor_name,
        "params": task.params,
        "input_file": task.input_file,
        "output_files": task.output_files,
        "extra_files": task.extra_files,
        "progress": task.progress,
        "message": task.message,
        "created_at": task.created_at.isoformat(),
    }


def _save_upload(file: UploadFile) -> str:
    unique_name = f"{uuid.uuid4()}_{file.filename or 'upload.bin'}"
    destination = Path(settings.UPLOAD_DIR) / unique_name
    with destination.open("wb") as out:
        out.write(file.file.read())
    return str(destination)


def _normalize_idempotency_key(raw_key: str | None) -> str | None:
    if not isinstance(raw_key, str):
        return None
    key = raw_key.strip()
    if not key:
        return None
    if len(key) > 128:
        return key[:128]
    return key


def _idempotency_redis_key(normalized_key: str) -> str:
    return f"{IDEMPOTENCY_KEY_PREFIX}{normalized_key}"


def _find_reusable_task_id(normalized_key: str) -> str | None:
    redis_key = _idempotency_redis_key(normalized_key)
    raw = task_store.redis.get(redis_key)
    if raw is None:
        return None

    task_id = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
    task = task_store.get(task_id)
    if task is None:
        task_store.redis.delete(redis_key)
        return None
    if task.status in {TaskStatus.FAILED, TaskStatus.CANCELED}:
        task_store.redis.delete(redis_key)
        return None
    return task.id


def _bind_idempotency_key(normalized_key: str, task_id: str) -> None:
    redis_key = _idempotency_redis_key(normalized_key)
    task_store.redis.setex(redis_key, settings.TASK_IDEMPOTENCY_TTL_SECONDS, task_id)


@router.post("")
async def create_task(
    input_file: UploadFile = File(...),
    extra_files: list[UploadFile] = File(default_factory=list),
    processor: str = Form(...),
    params: str = Form("{}"),
    idempotency_key: str | None = Form(default=None),
) -> dict:
    try:
        parsed_params = json.loads(params)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid params JSON") from exc

    normalized_key = _normalize_idempotency_key(idempotency_key)
    if normalized_key is not None:
        reusable_task_id = _find_reusable_task_id(normalized_key)
        if reusable_task_id is not None:
            return {"task_id": reusable_task_id, "reused": True}

    input_path = _save_upload(input_file)
    extra_file_map: dict[str, str] = {}
    for index, file in enumerate(extra_files):
        saved = _save_upload(file)
        key = file.filename or f"file_{index}"
        extra_file_map[key] = saved

    task = Task(
        id=str(uuid.uuid4()),
        status=TaskStatus.PENDING,
        processor_name=processor,
        params=parsed_params,
        input_file=input_path,
        output_files=[],
        extra_files=extra_file_map,
        progress=0,
        message="pending",
    )
    task_store.save(task)
    if normalized_key is not None:
        _bind_idempotency_key(normalized_key, task.id)
    process_task.delay(task.id)
    return {"task_id": task.id}


@router.get("/{task_id}")
async def get_task(task_id: str) -> dict:
    task = task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return serialize_task(task)


@router.get("/{task_id}/download")
async def download_task_result(task_id: str):
    task = task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.output_files:
        raise HTTPException(status_code=404, detail="Task has no output files")

    if len(task.output_files) == 1:
        file_path = Path(task.output_files[0])
        return FileResponse(file_path, filename=file_path.name)

    zip_path = Path(settings.OUTPUT_DIR) / f"{task.id}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for output_file in task.output_files:
            output_path = Path(output_file)
            if output_path.exists():
                bundle.write(output_path, arcname=output_path.name)
    return FileResponse(zip_path, filename=zip_path.name)


@router.get("/{task_id}/outputs/{index}")
async def get_task_output_file(task_id: str, index: int):
    task = task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if index < 0 or index >= len(task.output_files):
        raise HTTPException(status_code=404, detail="Output file not found")

    output_path = Path(task.output_files[index])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file missing on server")
    return FileResponse(output_path, filename=output_path.name)


@router.delete("/{task_id}")
async def cancel_or_delete_task(task_id: str) -> dict:
    task = task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    process_task.AsyncResult(task_id).revoke(terminate=True)

    task.status = TaskStatus.CANCELED
    task.message = "canceled"
    task_store.save(task)
    publish_progress(task.id, task.progress, task.message, task.status.value)

    file_paths = [task.input_file, *task.extra_files.values(), *task.output_files]
    for file_path in file_paths:
        path = Path(file_path)
        if path.exists():
            path.unlink()

    return {"task_id": task.id, "status": task.status.value}
