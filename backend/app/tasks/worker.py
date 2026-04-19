from __future__ import annotations

import json

import redis
from celery import Celery

from app.config import settings
from app.core.registry import ProcessorRegistry
from app.models.task import TaskStatus, task_store

celery_app = Celery("gameasset", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
redis_client = redis.Redis.from_url(settings.REDIS_URL)


def publish_progress(task_id: str, progress: int, message: str, status: str) -> None:
    payload = {
        "task_id": task_id,
        "progress": progress,
        "message": message,
        "status": status,
    }
    redis_client.publish(f"task:{task_id}", json.dumps(payload))


def run_process_task(task_id: str) -> None:
    task = task_store.get(task_id)
    if task is None:
        raise ValueError(f"Task not found: {task_id}")

    try:
        task.status = TaskStatus.PROCESSING
        task.message = "processing"
        task_store.save(task)
        publish_progress(task.id, task.progress, task.message, task.status.value)

        processor = ProcessorRegistry.get(task.processor_name)
        process_params = dict(task.params)
        process_params.update({"extra_files": task.extra_files})

        if not processor.validate(process_params):
            raise ValueError("Processor validation failed")

        def progress_callback(progress: int, message: str) -> None:
            task.progress = progress
            task.message = message
            task.status = TaskStatus.PROCESSING
            task_store.save(task)
            publish_progress(task.id, progress, message, task.status.value)

        outputs = processor.process(
            input_file=task.input_file,
            output_dir=settings.OUTPUT_DIR,
            params=process_params,
            progress_callback=progress_callback,
        )

        task.output_files = outputs
        task.progress = 100
        task.message = "completed"
        task.status = TaskStatus.COMPLETED
        task_store.save(task)
        publish_progress(task.id, task.progress, task.message, task.status.value)
    except Exception as exc:
        task.status = TaskStatus.FAILED
        task.message = str(exc)
        task_store.save(task)
        publish_progress(task.id, task.progress, task.message, task.status.value)


@celery_app.task(name="process_task")
def process_task(task_id: str) -> None:
    run_process_task(task_id)
