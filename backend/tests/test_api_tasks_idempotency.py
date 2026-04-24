from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from app.api import tasks as tasks_api
from app.models.task import Task, TaskStatus


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str):
        value = self.store.get(key)
        if value is None:
            return None
        return value.encode("utf-8")

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    def delete(self, key: str) -> None:
        self.store.pop(key, None)


class _FakeTaskStore:
    def __init__(self) -> None:
        self.redis = _FakeRedis()
        self.tasks: dict[str, Task] = {}
        self.save_calls = 0

    def save(self, task: Task) -> None:
        self.tasks[task.id] = task
        self.save_calls += 1

    def get(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)


class _FakeProcessTask:
    def __init__(self) -> None:
        self.delay_calls: list[str] = []

    def delay(self, task_id: str) -> None:
        self.delay_calls.append(task_id)


def _upload_file(name: str, payload: bytes = b"demo") -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(payload))


def test_create_task_reuses_task_id_with_same_idempotency_key(tmp_path, monkeypatch) -> None:
    fake_store = _FakeTaskStore()
    fake_process_task = _FakeProcessTask()
    monkeypatch.setattr(tasks_api, "task_store", fake_store)
    monkeypatch.setattr(tasks_api, "process_task", fake_process_task)
    monkeypatch.setattr(tasks_api.settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    Path(tasks_api.settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    first = asyncio.run(
        tasks_api.create_task(
            input_file=_upload_file("first.png", b"first"),
            extra_files=[],
            processor="image.cutout",
            params="{}",
            idempotency_key="demo-key",
        )
    )
    second = asyncio.run(
        tasks_api.create_task(
            input_file=_upload_file("second.png", b"second"),
            extra_files=[],
            processor="image.cutout",
            params="{}",
            idempotency_key="demo-key",
        )
    )

    assert second["task_id"] == first["task_id"]
    assert second["reused"] is True
    assert fake_store.save_calls == 1
    assert len(fake_process_task.delay_calls) == 1


def test_create_task_allows_retry_when_previous_task_failed(tmp_path, monkeypatch) -> None:
    fake_store = _FakeTaskStore()
    fake_process_task = _FakeProcessTask()
    monkeypatch.setattr(tasks_api, "task_store", fake_store)
    monkeypatch.setattr(tasks_api, "process_task", fake_process_task)
    monkeypatch.setattr(tasks_api.settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    Path(tasks_api.settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    first = asyncio.run(
        tasks_api.create_task(
            input_file=_upload_file("first.png", b"first"),
            extra_files=[],
            processor="image.cutout",
            params="{}",
            idempotency_key="demo-key-retry",
        )
    )
    fake_store.tasks[first["task_id"]].status = TaskStatus.FAILED

    second = asyncio.run(
        tasks_api.create_task(
            input_file=_upload_file("second.png", b"second"),
            extra_files=[],
            processor="image.cutout",
            params="{}",
            idempotency_key="demo-key-retry",
        )
    )

    assert second["task_id"] != first["task_id"]
    assert "reused" not in second
    assert fake_store.save_calls == 2
    assert len(fake_process_task.delay_calls) == 2
