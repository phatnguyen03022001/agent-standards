#!/usr/bin/env python3
"""Run repository-owned Generation 1 verification without writing bytecode."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    commands = (
        [sys.executable, "-B", "tools/validate.py"],
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
    )
    for command in commands:
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
