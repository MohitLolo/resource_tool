from datetime import datetime, timezone

from app.models.task import RedisTaskStore, Task, TaskStatus


class FakeRedis:
    def __init__(self) -> None:
        self.hashes = {}
        self.sorted = {}

    def hset(self, key, mapping):
        self.hashes[key] = {k: str(v) for k, v in mapping.items()}

    def hgetall(self, key):
        return self.hashes.get(key, {})

    def delete(self, key):
        self.hashes.pop(key, None)

    def zadd(self, key, mapping):
        bucket = self.sorted.setdefault(key, {})
        for member, score in mapping.items():
            bucket[member] = score

    def zrevrange(self, key, start, end):
        members = self.sorted.get(key, {})
        ordered = sorted(members.items(), key=lambda x: x[1], reverse=True)
        slice_end = None if end == -1 else end + 1
        return [member for member, _ in ordered[start:slice_end]]


def test_task_serialization_roundtrip() -> None:
    now = datetime(2026, 4, 18, 15, 30, tzinfo=timezone.utc)
    task = Task(
        id="t1",
        status=TaskStatus.PENDING,
        processor_name="image.crop",
        params={"width": 128},
        input_file="/tmp/in.png",
        output_files=["/tmp/out.png"],
        extra_files={"mask_file": "/tmp/mask.png"},
        progress=10,
        message="queued",
        created_at=now,
    )

    encoded = task.to_dict()
    restored = Task.from_dict(encoded)

    assert restored.id == "t1"
    assert restored.status == TaskStatus.PENDING
    assert restored.params["width"] == 128
    assert restored.output_files == ["/tmp/out.png"]
    assert restored.extra_files["mask_file"] == "/tmp/mask.png"
    assert restored.created_at == now


def test_redis_task_store_save_get_delete_and_list_recent() -> None:
    redis = FakeRedis()
    store = RedisTaskStore(redis_client=redis)

    task1 = Task(
        id="a",
        status=TaskStatus.PROCESSING,
        processor_name="image.pixelate",
        params={},
        input_file="a.png",
        output_files=[],
        extra_files={},
        progress=20,
        message="running",
    )
    task2 = Task(
        id="b",
        status=TaskStatus.COMPLETED,
        processor_name="image.convert",
        params={},
        input_file="b.png",
        output_files=["b.webp"],
        extra_files={},
        progress=100,
        message="done",
    )

    store.save(task1)
    store.save(task2)

    loaded = store.get("a")
    assert loaded is not None
    assert loaded.status == TaskStatus.PROCESSING

    recent = store.list_recent(limit=2)
    assert {task.id for task in recent} == {"a", "b"}

    store.delete("a")
    assert store.get("a") is None
