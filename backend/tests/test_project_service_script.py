from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _make_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_project_service_start_skips_redis_binary_check_when_redis_is_running(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls_file = tmp_path / "calls.txt"

    _make_executable(
        fake_bin / "pgrep",
        """#!/usr/bin/env bash
if [[ "$*" == *"redis-server.*:6379"* ]]; then
  echo "1234"
  exit 0
fi
exit 1
""",
    )
    _make_executable(
        fake_bin / "pkill",
        """#!/usr/bin/env bash
exit 0
""",
    )
    _make_executable(
        fake_bin / "curl",
        """#!/usr/bin/env bash
exit 0
""",
    )
    _make_executable(
        fake_bin / "conda",
        f"""#!/usr/bin/env bash
echo "conda $*" >> "{calls_file}"
exit 0
""",
    )
    _make_executable(
        fake_bin / "npm",
        f"""#!/usr/bin/env bash
echo "npm $*" >> "{calls_file}"
exit 0
""",
    )
    _make_executable(
        fake_bin / "nohup",
        """#!/usr/bin/env bash
"$@"
""",
    )
    _make_executable(
        fake_bin / "sleep",
        """#!/usr/bin/env bash
exit 0
""",
    )
    script = Path("/home/huangnianzhi/tools/scripts/project_service.sh")
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["LOG_DIR"] = str(tmp_path / "logs")

    result = subprocess.run(
        ["bash", str(script), "start"],
        cwd="/home/huangnianzhi/tools",
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "[skip] redis already running" in result.stdout

