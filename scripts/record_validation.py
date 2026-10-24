"""Record actual required checks for a clean revision, retaining failures honestly."""

import json
import platform
import sys
from pathlib import Path

from clean_clone import run_command
from project import ROOT, code_digest, git, now, save_report

TARGETS = ("doctor", "validate", "demo", "security")
NOT_RUN = [
    "AWS authenticated plan/apply, cloud IAM/reachability and backend recovery: unauthorized",
    "Terraform-engine compatibility: unverified",
]


def main():
    revision = git(["rev-parse", "HEAD"])
    if git(["status", "--porcelain"]):
        raise SystemExit("Commit reviewed changes first; formal evidence requires clean source")
    fingerprint = code_digest()
    destination = ROOT / "evidence" / (revision[:12] + "-controller.json")
    if destination.exists():
        raise SystemExit("Preserve existing evidence; use a new tested revision")
    report = {
        "schema_version": 1,
        "revision": revision,
        "code_fingerprint": fingerprint,
        "profile": "controller",
        "clean_at_start": True,
        "started_at": now(),
        "environment": {
            "os": platform.system(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
        },
        "commands": [],
        "not_run": NOT_RUN,
        "cloud_resources_created": False,
    }
    summary = ROOT / ".runtime/mock-output/summary.json"
    if summary.exists():
        summary.unlink()
    for target in TARGETS:
        result = run_command(
            ["make", target], ROOT, {str(ROOT): "$REPO", str(Path.home()): "$HOME"}, timeout=600
        )
        report["commands"].append(result)
        print(f"make {target}: exit {result['exit_code']}", flush=True)
        if result["exit_code"]:
            print(result["output"][-12000:], flush=True)
    report["native_mock_results"] = (
        json.loads(summary.read_text()) if summary.exists() else None
    )
    report["source_unchanged"] = (
        not git(["status", "--porcelain"]) and code_digest() == fingerprint
    )
    report["finished_at"] = now()
    report["passed"] = (
        report["source_unchanged"]
        and all(item["exit_code"] == 0 for item in report["commands"])
        and report["native_mock_results"] is not None
    )
    save_report(report, destination)
    print(destination.relative_to(ROOT))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
