#!/usr/bin/env python3
"""Rebase only the public S3 example settings from a historical Git mail."""
from pathlib import Path
import sys


def rebase(root: Path, patch: Path) -> None:
    env = root / ".env.example"
    text = env.read_text()
    mail = patch.read_text()
    header = "diff --git a/.env.example b/.env.example\n"
    if mail.count(header) != 1:
        raise ValueError("S3 mail must contain one .env.example diff")
    chunk = mail.split(header, 1)[1].split("\ndiff --git ", 1)[0]
    added = [line[1:] for line in chunk.splitlines()
             if line.startswith("+") and not line.startswith("+++")]
    if not any("S3_ACCESS_KEY" in line for line in added):
        raise ValueError("S3 configuration hunk missing")
    if "# S3_ACCESS_KEY" in text:
        raise ValueError("S3 configuration unexpectedly already exists in upstream")
    marker = "# === Common optional Settings"
    if text.count(marker) != 1:
        raise ValueError("Upstream config insertion point is ambiguous")
    env.write_text(text.replace(marker, "\n".join(added) + "\n" + marker))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: rebase_s3_env.py <upstream> <mail.diff>")
    rebase(Path(sys.argv[1]), Path(sys.argv[2]))
