from app.models.task import Task, TaskStatus
from app.api.tasks import serialize_task


def test_serialize_task_preserves_structured_fields() -> None:
    task = Task(
        id="x",
        status=TaskStatus.PENDING,
        processor_name="image.crop",
        params={"w": 1},
        input_file="in.png",
        output_files=["out.png"],
        extra_files={"mask": "mask.png"},
        progress=5,
        message="queued",
    )

    payload = serialize_task(task)

    assert payload["id"] == "x"
    assert payload["status"] == "pending"
    assert payload["params"]["w"] == 1
    assert payload["output_files"] == ["out.png"]
    assert payload["extra_files"]["mask"] == "mask.png"
