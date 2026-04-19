from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import redis

from app.config import settings


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class Task:
    id: str
    status: TaskStatus
    processor_name: str
    params: dict
    input_file: str
    output_files: list[str] = field(default_factory=list)
    extra_files: dict[str, str] = field(default_factory=dict)
    progress: int = 0
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "status": self.status.value,
            "processor_name": self.processor_name,
            "params": json.dumps(self.params),
            "input_file": self.input_file,
            "output_files": json.dumps(self.output_files),
            "extra_files": json.dumps(self.extra_files),
            "progress": str(self.progress),
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "Task":
        return cls(
            id=payload["id"],
            status=TaskStatus(payload["status"]),
            processor_name=payload["processor_name"],
            params=json.loads(payload.get("params", "{}")),
            input_file=payload["input_file"],
            output_files=json.loads(payload.get("output_files", "[]")),
            extra_files=json.loads(payload.get("extra_files", "{}")),
            progress=int(payload.get("progress", "0")),
            message=payload.get("message", ""),
            created_at=datetime.fromisoformat(payload["created_at"]),
        )


class RedisTaskStore:
    def __init__(
        self,
        redis_client: redis.Redis,
        task_prefix: str = "task:",
        recent_index_key: str = "tasks:recent",
    ) -> None:
        self.redis = redis_client
        self.task_prefix = task_prefix
        self.recent_index_key = recent_index_key

    def _task_key(self, task_id: str) -> str:
        return f"{self.task_prefix}{task_id}"

    def save(self, task: Task) -> None:
        key = self._task_key(task.id)
        self.redis.hset(key, mapping=task.to_dict())
        self.redis.zadd(self.recent_index_key, {task.id: task.created_at.timestamp()})

    def get(self, task_id: str) -> Task | None:
        payload = self.redis.hgetall(self._task_key(task_id))
        if not payload:
            return None

        normalized: dict[str, str] = {}
        for key, value in payload.items():
            k = key.decode("utf-8") if isinstance(key, bytes) else str(key)
            v = value.decode("utf-8") if isinstance(value, bytes) else str(value)
            normalized[k] = v
        return Task.from_dict(normalized)

    def delete(self, task_id: str) -> None:
        self.redis.delete(self._task_key(task_id))

    def list_recent(self, limit: int = 50) -> list[Task]:
        members = self.redis.zrevrange(self.recent_index_key, 0, max(0, limit - 1))
        task_ids = [
            member.decode("utf-8") if isinstance(member, bytes) else str(member)
            for member in members
        ]

        tasks: list[Task] = []
        for task_id in task_ids:
            task = self.get(task_id)
            if task is not None:
                tasks.append(task)
        return tasks


task_store = RedisTaskStore(redis.Redis.from_url(settings.REDIS_URL))
