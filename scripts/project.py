"""Revision identity and bounded repository-owned runtime paths."""

import datetime
import hashlib
import os
import stat
import subprocess
from pathlib import Path

from paths import bounded

ROOT = Path(__file__).resolve().parents[1]
STACKS = ("foundation", "state-bootstrap")
CODE_PATHS = (
    "modules",
    "stacks",
    "scripts",
    "tests",
    ".github",
    "Makefile",
    "pyproject.toml",
    "requirements.lock",
    "requirements-dev.lock",
    "tools.lock.json",
    "tools-iac.lock.json",
    ".tflint.hcl",
    ".python-version",
)


def now():
    return datetime.datetime.now(datetime.UTC).isoformat()


def git(args, root=ROOT):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def code_digest(root=ROOT):
    digest = hashlib.sha256()
    paths = []
    for name in CODE_PATHS:
        path = root / name
        paths.extend(path.rglob("*") if path.is_dir() else [path])
    for path in sorted(paths):
        if any(part in {".terraform", "__pycache__"} for part in path.parts):
            continue
        if path.is_symlink():
            raise ValueError("Symlink in implementation")
        if path.is_file():
            digest.update(
                path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes()
            )
    return digest.hexdigest()


def private_directory(path, root=ROOT):
    path = bounded(root, path)
    for item in reversed([path, *path.parents]):
        if item == root or not item.is_relative_to(root):
            continue
        item.mkdir(mode=0o700, exist_ok=True)
        info = item.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise ValueError("Private runtime ownership/mode mismatch")
    return path


def save_report(report, path, root=ROOT):
    import json

    path = bounded(root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
