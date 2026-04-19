from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import redis

from app.config import settings


EXPECTED_TYPES: dict[str, str] = {
    "unacked": "hash",
    "unacked_index": "zset",
    "unacked_mutex": "string",
}


@dataclass
class CheckResult:
    key: str
    expected: str
    actual: str


def expected_type_for_key(key: str) -> str | None:
    for suffix, expected in EXPECTED_TYPES.items():
        if key.endswith(suffix):
            return expected
    return None


def run_check(redis_url: str, delete_wrong_type: bool = False) -> list[CheckResult]:
    client = redis.Redis.from_url(redis_url)
    issues: list[CheckResult] = []

    for raw_key in client.scan_iter(match="*unacked*"):
        key = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else str(raw_key)
        expected = expected_type_for_key(key)
        if expected is None:
            continue

        raw_type = client.type(key)
        actual = raw_type.decode("utf-8") if isinstance(raw_type, bytes) else str(raw_type)
        if actual == expected:
            continue

        issues.append(CheckResult(key=key, expected=expected, actual=actual))
        if delete_wrong_type:
            client.delete(key)

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Check celery redis transport key types.")
    parser.add_argument("--redis-url", default=settings.REDIS_URL, help="Redis URL")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Delete keys with wrong type",
    )
    args = parser.parse_args()

    issues = run_check(args.redis_url, delete_wrong_type=args.fix)
    if not issues:
        print("OK: no wrong-type unacked keys")
        return 0

    action = "deleted" if args.fix else "found"
    print(f"WARN: {action} {len(issues)} wrong-type keys")
    for issue in issues:
        print(f"- {issue.key}: expected={issue.expected}, actual={issue.actual}")
    return 0 if args.fix else 2


if __name__ == "__main__":
    sys.exit(main())
