#!/usr/bin/env python3
"""Install checksum-verified developer tools inside this repository only.

Adapted from the portfolio's MIT-licensed local developer bootstrap.
Bundled third-party license members are retained when supplied by the archive.
"""

import hashlib
import io
import json
import platform
import subprocess
import tarfile
import urllib.request
import uuid
import venv
import zipfile
from pathlib import Path

from paths import bounded
from project import private_directory

ROOT = Path(__file__).resolve().parents[1]
PIP_WHEEL = (
    "https://files.pythonhosted.org/packages/3f/06/"
    "3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/"
    "pip-26.2.2-py3-none-any.whl"
    "#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
)


def prepare_environment(target):
    """Repair a project venv when a Homebrew interpreter upgrade removed its base."""
    interpreter = target / "bin/python"
    expected = (ROOT / ".python-version").read_text().strip()
    healthy = False
    if interpreter.exists():
        try:
            result = subprocess.run(
                [str(interpreter), "-c", "import platform; print(platform.python_version())"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            healthy = result.returncode == 0 and result.stdout.strip() == expected
        except OSError, subprocess.TimeoutExpired:
            pass
    if not healthy:
        # venv --upgrade can retain a copied macOS launcher linked to a removed
        # framework. Preserve the entire old environment, then create fresh paths.
        if target.exists():
            backups = private_directory(ROOT / ".runtime/venv-backups")
            backup = bounded(ROOT, backups / uuid.uuid4().hex)
            target.rename(backup)
            print("Preserved old virtual environment at " + str(backup.relative_to(ROOT)))
        venv.EnvBuilder(with_pip=True).create(target)
    # Python's 3.14.9 advisory explicitly supports this mitigation on 3.14.8:
    # install the hash-pinned pip/certifi fix before other package downloads.
    subprocess.run(
        [
            str(interpreter),
            "-m",
            "pip",
            "--isolated",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            "pip @ " + PIP_WHEEL,
        ],
        check=True,
        timeout=120,
    )


def main():
    expected = (ROOT / ".python-version").read_text().strip()
    if platform.python_version() != expected:
        raise SystemExit("Python " + expected + " is required by this locked controller stack")
    target = bounded(ROOT, ROOT / ".venv")
    prepare_environment(target)
    subprocess.run(
        [
            str(target / "bin/python"),
            "-m",
            "pip",
            "--isolated",
            "install",
            "--disable-pip-version-check",
            "--require-hashes",
            "--only-binary=:all:",
            "-r",
            str(ROOT / "requirements-dev.lock"),
        ],
        check=True,
        timeout=240,
    )
    arch = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "x86_64"}.get(platform.machine())
    key = f"{platform.system().lower()}-{arch}"
    manifest = json.loads((ROOT / "tools.lock.json").read_text())
    manifest["tools"].update(json.loads((ROOT / "tools-iac.lock.json").read_text())["tools"])
    output = bounded(ROOT, ROOT / ".tools/bin")
    output.mkdir(parents=True, exist_ok=True)
    for name, tool in manifest["tools"].items():
        if key not in tool["platforms"]:
            raise SystemExit(f"Unsupported developer-tool platform {key}: {name}")
        asset = tool["platforms"][key]
        binary = bounded(ROOT, output / name)
        marker = bounded(ROOT, output / (name + ".source-sha256"))
        # Recheck extracted binary to detect accidental local corruption.
        if binary.is_file() and marker.is_file():
            recorded = marker.read_text().split()
            if recorded == [asset["sha256"], hashlib.sha256(binary.read_bytes()).hexdigest()]:
                print(f"{name} {tool['version']}: verified cached installation")
                continue
        if not asset["url"].startswith("https://github.com/"):
            raise SystemExit("Only pinned official GitHub release downloads are permitted")
        print(f"Downloading {name} {tool['version']} ({key})", flush=True)
        with urllib.request.urlopen(asset["url"], timeout=90) as response:
            data = response.read(100_000_001)
        if len(data) > 100_000_000 or hashlib.sha256(data).hexdigest() != asset["sha256"]:
            raise SystemExit(f"Checksum/size mismatch for {name}; refusing installation")
        member = asset.get("member")
        if member and asset.get("archive") == "zip":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entry = archive.getinfo(member)
                if entry.is_dir() or entry.file_size > 150_000_000:
                    raise SystemExit(f"Unexpected ZIP binary for {name}")
                if asset.get("license_member"):
                    notice = archive.getinfo(asset["license_member"])
                    if notice.is_dir() or notice.file_size > 1_000_000:
                        raise SystemExit(f"Unexpected ZIP license for {name}")
                    directory = bounded(ROOT, ROOT / ".tools/licenses")
                    directory.mkdir(parents=True, exist_ok=True)
                    bounded(ROOT, directory / (name + ".txt")).write_bytes(archive.read(notice))
                data = archive.read(entry)
        elif member:
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                entry = archive.getmember(member)
                if not entry.isfile() or entry.size > 100_000_000:
                    raise SystemExit(f"Unexpected archive member for {name}")
                data = archive.extractfile(entry).read()
                if asset.get("license_member"):
                    notice = archive.getmember(asset["license_member"])
                    if not notice.isfile() or notice.size > 1_000_000:
                        raise SystemExit(f"Unexpected license member for {name}")
                    license_dir = bounded(ROOT, ROOT / ".tools/licenses")
                    license_dir.mkdir(parents=True, exist_ok=True)
                    bounded(ROOT, license_dir / (name + ".txt")).write_bytes(
                        archive.extractfile(notice).read()
                    )
        binary.write_bytes(data)
        binary.chmod(0o755)
        marker.write_text(asset["sha256"] + " " + hashlib.sha256(data).hexdigest() + "\n")
    print("Developer tools installed locally. No global packages changed.")


if __name__ == "__main__":
    main()
