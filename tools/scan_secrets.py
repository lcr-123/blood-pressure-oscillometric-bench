"""Scan the tracked tree for credentials that must never be published.

This repository ships firmware, tooling and a bench dataset. None of that needs
a password, an API key or a private key, so any hit here is either a mistake or
a file that must be sanitised before it is ever staged.

Usage
-----
    python tools/scan_secrets.py            # scan every tracked file
    python tools/scan_secrets.py --staged   # scan only what is staged
    python tools/scan_secrets.py --path X   # scan one file or directory

Exit code 0 means clean, 1 means at least one finding, 2 means the scan itself
could not run. Wire it into a pre-commit hook if you want the check to bite.

Why the patterns are not just "123456"
--------------------------------------
A bare digit string matches hundreds of legitimate places: Cortex-M headers use
123456 as a magic number, and the NDJSON captures contain it inside raw sample
values. Every pattern below therefore requires credential *context* -- a field
name, an assignment to a NAME that ends in PASSWORD/KEY/TOKEN, or a well-known
key header -- so that a hit means "this really is a secret", not "this file has
numbers in it".
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files we never read: binary captures and vendor blobs are not where secrets
# live, and decoding 2.4 GB of NDJSON would make the check useless in practice.
SKIP_SUFFIXES = {
    ".ndjson",
    ".jsonl",
    ".export.ndjson",
    ".png",
    ".pdf",
    ".docx",
    ".zip",
    ".exe",
    ".hex",
    ".bin",
    ".elf",
    ".o",
    ".a",
    ".axf",
}

# This file holds synthetic credential strings on purpose -- they are the test
# fixtures for the rules below, not secrets. Exempting it is stated here and
# reported in the output rather than done silently, so that a reviewer can see
# exactly one file is exempt and ask why if the list ever grows.
SKIP_FILES = {"tools/scan_secrets_selftest.py"}

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # A NAME = "value" assignment where NAME promises it holds a secret.
    (
        "assigned credential",
        re.compile(
            r"""(?ix)
            \b\w*(?:password|passwd|passcode|secret|token|api[_-]?key|
                  private[_-]?key|access[_-]?key)\w*
            \s*[:=]\s*
            ["'][^"'\s]{4,}["']
            """
        ),
    ),
    # The same assignment in a C/Arduino char array. Short names such as PASS[]
    # are common in embedded sketches, so they are included here.
    (
        "assigned credential (C string)",
        re.compile(
            r"""(?ix)
            \b\w*(?:PASSWORD|PASSWD|PASSCODE|PASS|PWD|SECRET|TOKEN|
                  APIKEY|API_KEY|PSK|WPA)\w*
            \s*\[\s*\]\s*=\s*"[^"]{4,}"
            """
        ),
    ),
    # A form field that ships with its password already filled in. The value
    # attribute may appear before or after the type, so check either order.
    (
        "password pre-filled in a form",
        re.compile(
            r"""(?ix)
            <input\b(?=[^>]*\btype\s*=\s*["']?password)(?=[^>]*\bvalue\s*=\s*
            ["'][^"']{3,}["'])[^>]*>
            """
        ),
    ),
    # An <input> whose id or name is "pass"/"password" and which carries a value.
    (
        "value shipped in a password field",
        re.compile(
            r"""(?ix)
            <input\b(?=[^>]*\b(?:id|name)\s*=\s*["']?[^"'>]*pass[^"'>]*)
            (?=[^>]*\bvalue\s*=\s*["'][^"']{3,}["'])[^>]*>
            """
        ),
    ),
    (
        "private key block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    ),
    (
        "AWS access key id",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "GitHub token",
        re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "Slack token",
        re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    ),
    (
        "bearer token",
        re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{20,}"),
    ),
    (
        "URL with embedded password",
        re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]{3,}@"),
    ),
    (
        "MQTT broker with inline credentials",
        re.compile(
            r"""(?ix)
            \busername_pw_set\s*\(\s*["'][^"']+["']\s*,\s*["'][^"']{3,}["']
            """
        ),
    ),
]

# Lines matching this are documentation about secrets, not secrets.
ALLOW_CONTEXT = re.compile(
    r"(?i)(scan_secrets|never\s+commit|do\s+not\s+commit|placeholder|"
    r"must\s+be\s+sanitis|redact|example\s+only|xxx+|<your|YOUR_|CHANGEME)"
)


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout
    return [ROOT / p.decode("utf-8") for p in out.split(b"\x00") if p]


def staged_files() -> list[Path]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return [ROOT / p.decode("utf-8") for p in out.split(b"\x00") if p]


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    for number, line in enumerate(text.splitlines(), 1):
        if ALLOW_CONTEXT.search(line):
            continue
        for label, pattern in PATTERNS:
            m = pattern.search(line)
            if m:
                snippet = line.strip()
                if len(snippet) > 120:
                    snippet = snippet[:117] + "..."
                hits.append((number, label, snippet))
                break
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--staged", action="store_true", help="scan only staged files")
    ap.add_argument("--path", help="scan one file or directory instead of the tree")
    args = ap.parse_args(argv)

    if args.path:
        target = Path(args.path)
        if not target.is_absolute():
            target = ROOT / target
        if not target.exists():
            # Scanning nothing and printing "clean" is worse than useless: it
            # reads as proof that a directory is free of secrets. Exit 2 is the
            # documented code for "the scan could not run".
            print(
                f"cannot scan {target}: no such file or directory",
                file=sys.stderr,
            )
            return 2
        if target.is_dir():
            files = [p for p in sorted(target.rglob("*")) if p.is_file()]
        else:
            files = [target]
    elif args.staged:
        files = staged_files()
    else:
        files = tracked_files()

    files = [p for p in files if p.suffix not in SKIP_SUFFIXES]

    skipped: list[str] = []
    kept: list[Path] = []
    for p in files:
        try:
            rel = p.relative_to(ROOT).as_posix()
        except ValueError:
            rel = p.as_posix()
        if rel in SKIP_FILES:
            skipped.append(rel)
        else:
            kept.append(p)
    files = kept
    for rel in skipped:
        print(f"note: exempt (holds test fixtures, not secrets): {rel}")

    findings = 0
    for path in files:
        for number, label, snippet in scan_file(path):
            try:
                shown = path.relative_to(ROOT)
            except ValueError:
                shown = path
            print(f"{shown}:{number}: {label}: {snippet}")
            findings += 1

    scanned = len(files)
    if findings:
        print(
            f"\nSECRETS FOUND: {findings} hit(s) across {scanned} file(s). "
            "Sanitise before staging.",
            file=sys.stderr,
        )
        return 1
    print(f"clean: {scanned} file(s) scanned, no credential patterns matched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
