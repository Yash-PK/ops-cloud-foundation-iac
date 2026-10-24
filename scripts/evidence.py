"""Require successful clean-source evidence matching the current implementation."""

import hashlib
import json
import re
import subprocess

from project import CODE_PATHS, ROOT, code_digest, git
from record_validation import NOT_RUN, TARGETS


def fingerprint_at(revision):
    digest = hashlib.sha256()
    names = git(["ls-tree", "-r", "--name-only", revision, "--", *CODE_PATHS]).splitlines()
    for name in sorted(names):
        if any(part in {".terraform", "__pycache__"} for part in name.split("/")):
            continue
        blob = subprocess.check_output(["git", "show", revision + ":" + name], cwd=ROOT)
        digest.update(name.encode() + b"\0" + blob)
    return digest.hexdigest()


def commands_passed(commands):
    return (
        isinstance(commands, list)
        and bool(commands)
        and all(
            isinstance(item, dict)
            and type(item.get("exit_code")) is int
            and item["exit_code"] == 0
            and item.get("timed_out") is False
            and isinstance(item.get("output"), str)
            for item in commands
        )
    )


def valid_report(report, profile, fingerprint):
    if (
        not isinstance(report, dict)
        or report.get("profile") != profile
        or report.get("passed") is not True
        or report.get("clean_at_start") is not True
        or report.get("code_fingerprint") != fingerprint
        or not re.fullmatch("[0-9a-f]{40}", report.get("revision", ""))
        or not report.get("started_at")
        or not report.get("finished_at")
        or not commands_passed(report.get("commands"))
    ):
        return False
    commands = report["commands"]
    if profile == "controller":
        if (
            report.get("not_run") != NOT_RUN
            or report.get("cloud_resources_created") is not False
            or report.get("source_unchanged") is not True
            or [item["argv"] for item in commands] != [["make", target] for target in TARGETS]
        ):
            return False
        mocks = report.get("native_mock_results", {})
        if set(mocks) != {"foundation", "state-bootstrap"}:
            return False
        for stack, count, plans in [("foundation", 16, 5), ("state-bootstrap", 7, 3)]:
            result = mocks[stack]
            summary = result.get("native_summary", {})
            if summary.get("passed") != count or any(
                summary.get(key, 0) != 0 for key in ["failed", "errored", "skipped"]
            ):
                return False
            accepted, rejected = (
                result.get("policy_plans", {}),
                result.get("negative_policies", []),
            )
            if (
                len(accepted) != plans
                or len(rejected) != 8
                or not all(
                    item.get("rejected") is True and item.get("reason") for item in rejected
                )
            ):
                return False
    elif profile == "clean-clone":
        if report.get("not_run") != [] or report.get("temporary_clone_removed") is not True:
            return False
        assertions = report.get("assertions", [])
        if {item.get("name") for item in assertions} != {
            "clone_revision_matches_source",
            "clone_remains_clean_after_checks",
        } or not all(item.get("passed") is True for item in assertions):
            return False
        make = [item["argv"] for item in commands if item["argv"][0] == "make"]
        if len(make) != 5 or [argv[-1] for argv in make] != [
            "bootstrap",
            "doctor",
            "validate",
            "demo",
            "security",
        ]:
            return False
    else:
        return False
    return True


def main():
    fingerprint = code_digest()
    found = {}
    for path in sorted((ROOT / "evidence").glob("*.json")):
        report = json.loads(path.read_text())
        profile = report.get("profile")
        if not valid_report(report, profile, fingerprint):
            continue
        revision = report["revision"]
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", revision, "HEAD"], cwd=ROOT, check=False
        )
        if ancestor.returncode == 0 and fingerprint_at(revision) == fingerprint:
            found[profile] = {"report": path.name, "tested_revision": revision}
    if set(found) != {"controller", "clean-clone"}:
        raise SystemExit(
            "Required current controller/clean-clone evidence missing or failed; "
            "release blocked"
        )
    print(
        json.dumps(
            {
                "local_gate": "passed",
                "code_fingerprint": fingerprint,
                "evidence": found,
                "cloud": "not deployed",
                "hosted_ci": "must inspect exact commit independently",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
