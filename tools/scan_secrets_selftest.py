"""Prove that tools/scan_secrets.py catches secrets and ignores look-alikes.

The scanner is only worth having if it is both sensitive and quiet. This test
feeds it one string at a time through the same pattern table the tool uses, so
it checks the rules rather than a hand-copied copy of them.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_tool():
    path = ROOT / "tools" / "scan_secrets.py"
    spec = importlib.util.spec_from_file_location("scan_secrets", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def matches(module, line: str) -> list[str]:
    labels = []
    if module.ALLOW_CONTEXT.search(line):
        return labels
    for label, pattern in module.PATTERNS:
        if pattern.search(line):
            labels.append(label)
    return labels


MUST_CATCH = [
    # the shapes that were actually present in the untracked cloud/ prototype
    'static const char WIFI_PASSWORD[] = "123456@@";',
    'static const char MQTT_PASSWORD[] = "123456";',
    'static const char PASS[] = "123456@@";',
    'c.username_pw_set("bp-device-001", "123456")',
    '<input id="pass" value="123456" type="password">',
    '<input type="password" value="123456" id="pass">',
    # generic shapes any future file might carry
    'password = "hunter2hunter2"',
    'api_key: "abcdef0123456789"',
    "-----BEGIN RSA PRIVATE KEY-----",
    "AKIAIOSFODNN7EXAMPLE",
    "ghp_0123456789abcdefghijklmnopqrstuvwx",
    "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345",
    "mqtt://user:s3cr3t@broker.example.com",
    'token = "ya29.a0AfH6SMB1234567890"',
]

MUST_IGNORE = [
    # legitimate numbers and identifiers that a naive digits-only rule flags
    "matrix[0] = 123456;",
    "0x12345678",
    "i2c address 0x48",
    'raw=123456 ads=100mV sensor=200mV est=5.0mmHg VALID',
    "115200 8N1",
    # documentation *about* secrets
    "# 先脱敏，然后跑 python tools/scan_secrets.py",
    "placeholder: replace PASSWORD with an environment variable",
    "do not commit a private key here",
    # ordinary prose
    "the token bucket holds 60 rounds",
    "password prompt appears once",
]


def main() -> int:
    module = load_tool()
    failures: list[str] = []

    for line in MUST_CATCH:
        got = matches(module, line)
        if not got:
            failures.append(f"MISSED: {line}")
        else:
            print(f"  caught  [{got[0]}]  {line[:70]}")

    for line in MUST_IGNORE:
        got = matches(module, line)
        if got:
            failures.append(f"FALSE POSITIVE: {line}  -> {got}")
        else:
            print(f"  ignored                {line[:70]}")

    if failures:
        print("\nFAILURES:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print(
        f"\nSELFTEST OK: {len(MUST_CATCH)} secret shapes caught, "
        f"{len(MUST_IGNORE)} look-alikes ignored"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
