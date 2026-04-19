from app.models.task import Task, TaskStatus
from app.tasks import worker


class FakeStore:
    def __init__(self, task: Task) -> None:
        self.task = task
        self.saved = []

    def get(self, task_id: str):
        if self.task.id == task_id:
            return self.task
        return None

    def save(self, task: Task):
        self.saved.append((task.status, task.progress, task.message, list(task.output_files)))


class OkProcessor:
    def validate(self, params: dict) -> bool:
        return True

    def process(self, input_file, output_dir, params, progress_callback):
        progress_callback(45, "half")
        return ["out.png"]


class BadProcessor:
    def validate(self, params: dict) -> bool:
        return False

    def process(self, input_file, output_dir, params, progress_callback):
        raise AssertionError("should not run")


def test_run_process_task_completes_and_reports_progress(monkeypatch) -> None:
    task = Task(
        id="t1",
        status=TaskStatus.PENDING,
        processor_name="image.crop",
        params={},
        input_file="in.png",
    )
    store = FakeStore(task)
    published = []

    monkeypatch.setattr(worker, "task_store", store)
    monkeypatch.setattr(worker.ProcessorRegistry, "get", lambda _name: OkProcessor())
    monkeypatch.setattr(worker, "publish_progress", lambda tid, p, m, s: published.append((tid, p, m, s)))

    worker.run_process_task("t1")

    assert task.status == TaskStatus.COMPLETED
    assert task.progress == 100
    assert task.output_files == ["out.png"]
    assert any(item[1] == 45 for item in published)
    assert published[-1][3] == TaskStatus.COMPLETED.value


def test_run_process_task_marks_failed_when_validation_fails(monkeypatch) -> None:
    task = Task(
        id="t2",
        status=TaskStatus.PENDING,
        processor_name="image.crop",
        params={},
        input_file="in.png",
    )
    store = FakeStore(task)
    published = []

    monkeypatch.setattr(worker, "task_store", store)
    monkeypatch.setattr(worker.ProcessorRegistry, "get", lambda _name: BadProcessor())
    monkeypatch.setattr(worker, "publish_progress", lambda tid, p, m, s: published.append((tid, p, m, s)))

    worker.run_process_task("t2")

    assert task.status == TaskStatus.FAILED
    assert "validation" in task.message.lower()
    assert published[-1][3] == TaskStatus.FAILED.value
