from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _make_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_start_celery_worker_uses_solo_pool_and_restarts_on_failure(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    state_file = tmp_path / "celery-count.txt"
    args_file = tmp_path / "celery-args.txt"
    python_calls = tmp_path / "python-calls.txt"

    _make_executable(
        fake_bin / "python",
        f"""#!/usr/bin/env bash
echo "$@" >> "{python_calls}"
exit 0
""",
    )
    _make_executable(
        fake_bin / "celery",
        f"""#!/usr/bin/env bash
count=0
if [[ -f "{state_file}" ]]; then
  count="$(cat "{state_file}")"
fi
count=$((count + 1))
echo "$count" > "{state_file}"
printf '%s\\n' "$*" >> "{args_file}"
if [[ "$count" -lt 3 ]]; then
  exit 1
fi
exit 0
""",
    )

    script = Path("/home/huangnianzhi/tools/backend/scripts/start_celery_worker.sh")
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["RESTART_DELAY"] = "0"
    env["MAX_RESTARTS"] = "5"

    result = subprocess.run(
        ["bash", str(script)],
        cwd="/home/huangnianzhi/tools",
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert state_file.read_text(encoding="utf-8").strip() == "3"
    assert "-P solo" in args_file.read_text(encoding="utf-8")
    assert python_calls.read_text(encoding="utf-8").count("scripts/check_celery_redis_state.py") == 1

