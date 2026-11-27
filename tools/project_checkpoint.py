#!/usr/bin/env python3

"""
BEHZAD_AI Project Checkpoint

Purpose:
Create a project inventory and environment snapshot.

Safety:
- Does not modify source files.
- Does not access databases.
- Does not move or delete files.
- Does not change storage paths.
"""

import os
import sys
import platform
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports"
REPORT_FILE = REPORT_DIR / "checkpoint.txt"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
}

SKIP_FILES = {
    ".pyc",
}


def get_git_status():
    """Read git status without modifying repository."""

    git_dir = ROOT / ".git"

    if not git_dir.exists():
        return "Git repository not detected."

    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--short"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return result.stderr.strip() or "Git status unavailable."

        output = result.stdout.strip()

        return output if output else "Working tree clean."

    except Exception as exc:
        return f"Git status error: {exc}"


def collect_files():
    """Collect relative paths of project files."""

    files = []

    for current_root, dirs, filenames in os.walk(ROOT):

        dirs[:] = sorted(
            d for d in dirs
            if d not in SKIP_DIRS
        )

        current = Path(current_root)

        for filename in sorted(filenames):

            if filename in SKIP_FILES:
                continue

            path = current / filename

            try:
                relative = path.relative_to(ROOT)
                files.append(str(relative))
            except ValueError:
                continue

    return sorted(files)


def main():

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    now = datetime.now().astimezone()

    files = collect_files()

    python_info = (
        f"Python: {sys.version.replace(chr(10), ' ')}"
    )

    git_status = get_git_status()

    lines = []

    lines.append("=" * 70)
    lines.append("BEHZAD_AI PROJECT CHECKPOINT")
    lines.append("=" * 70)

    lines.append(f"Timestamp: {now.isoformat()}")
    lines.append(f"Project root: {ROOT}")
    lines.append(f"Platform: {platform.platform()}")
    lines.append(python_info)

    lines.append("")
    lines.append("GIT STATUS")
    lines.append("-" * 70)
    lines.append(git_status)

    lines.append("")
    lines.append("PROJECT FILE INVENTORY")
    lines.append("-" * 70)
    lines.append(f"Total files: {len(files)}")

    for file_path in files:
        lines.append(file_path)

    lines.append("")
    lines.append("IMPORTANT PROJECT RECORDS")
    lines.append("-" * 70)

    for name in (
        "PROJECT_STATE.md",
        "PROJECT_LOG.md",
        "CONTINUE_HERE.txt",
    ):

        path = ROOT / name

        status = "EXISTS" if path.exists() else "MISSING"

        lines.append(f"{name}: {status}")

    lines.append("")
    lines.append("SAFETY")
    lines.append("-" * 70)
    lines.append("No database was opened.")
    lines.append("No source files were modified.")
    lines.append("No project files were deleted.")
    lines.append("No storage paths were changed.")

    lines.append("")
    lines.append("=" * 70)

    report = "\n".join(lines)

    REPORT_FILE.write_text(
        report,
        encoding="utf-8"
    )

    print(report)

    print("")
    print(f"Checkpoint saved: {REPORT_FILE}")


if __name__ == "__main__":
    main()
