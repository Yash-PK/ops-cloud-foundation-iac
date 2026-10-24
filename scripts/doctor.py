"""Inspect required tool versions without credentials or host configuration changes."""

import json
import platform
import subprocess
import sys

from project import ROOT


def main():
    expected_python = (ROOT / ".python-version").read_text().strip()
    if platform.python_version() != expected_python:
        raise SystemExit("Required tested interpreter: Python " + expected_python)
    print(
        json.dumps(
            {
                "os": platform.system(),
                "release": platform.release(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
                "cloud": "disabled",
                "virtualization": "not needed",
                "privilege": "unprivileged",
                "requirements": (
                    "2 CPU / 2 GiB RAM / 3 GiB disk recommended; "
                    "bootstrap network; sequential tests"
                ),
            },
            indent=2,
        )
    )
    versions = {
        "tofu": ("1.13.1", ["version"]),
        "tflint": ("0.64.0", ["--version"]),
        "shellcheck": ("0.11.0", ["--version"]),
        "shfmt": ("3.14.1", ["--version"]),
        "actionlint": ("1.7.12", ["--version"]),
        "gitleaks": ("8.30.1", ["version"]),
    }
    for name, (expected, args) in versions.items():
        result = subprocess.run(
            [str(ROOT / ".tools/bin" / name), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        if expected not in result.stdout:
            raise SystemExit("Tool version mismatch: " + name)
        print(name + ": " + expected)
    import hcl2

    print("python-hcl2: " + hcl2.__version__)
    print("Live plans, cloud apply/destroy, billing and credential discovery are unauthorized.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
