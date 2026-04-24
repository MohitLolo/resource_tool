from app import main


def test_health_returns_ok_when_all_components_ready(monkeypatch) -> None:
    monkeypatch.setattr(main, "_redis_is_ready", lambda: True)
    monkeypatch.setattr(main, "_worker_is_ready", lambda: True)
    payload = main.health()
    assert payload["status"] == "ok"
    assert payload["api"] == "ok"
    assert payload["redis"] == "ok"
    assert payload["worker"] == "ok"


def test_health_returns_degraded_when_worker_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(main, "_redis_is_ready", lambda: True)
    monkeypatch.setattr(main, "_worker_is_ready", lambda: False)
    payload = main.health()
    assert payload["status"] == "degraded"
    assert payload["redis"] == "ok"
    assert payload["worker"] == "down"
