"""Bounded local OpenTofu operations; live plans and mutations are disabled."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from guard import GuardError, parse, preflight
from paths import bounded
from policy import check_plan, negative_controls
from project import ROOT, STACKS, private_directory


def environment(root=ROOT, *, network=False):
    runtime = private_directory(root / ".runtime", root)
    home = private_directory(runtime / "empty-home", root)
    cache = private_directory(runtime / "provider-cache", root)
    config = bounded(root, runtime / "tofu.tfrc")
    config.write_text(
        "provider_installation {\n  direct {\n"
        '    include = ["registry.terraform.io/hashicorp/aws"]\n'
        "  }\n}\ndisable_checkpoint = true\n"
    )
    config.chmod(0o600)
    empty = bounded(root, home / "empty")
    empty.write_text("")
    empty.chmod(0o600)
    env = {
        "PATH": str(root / ".tools/bin") + ":/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(home),
        "LC_ALL": "C.UTF-8",
        "TF_CLI_CONFIG_FILE": str(config),
        "TF_PLUGIN_CACHE_DIR": str(cache),
        "TF_IN_AUTOMATION": "1",
        "TF_INPUT": "false",
        "CHECKPOINT_DISABLE": "1",
        "AWS_EC2_METADATA_DISABLED": "true",
        "AWS_CONFIG_FILE": str(empty),
        "AWS_SHARED_CREDENTIALS_FILE": str(empty),
    }
    if not network:
        # Defense in depth, not an OS network sandbox. Native mock providers are the
        # primary API-call boundary. No credential/environment inheritance occurs.
        env.update(
            {key: "http://127.0.0.1:9" for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")}
        )
        env["NO_PROXY"] = ""
    return env


def run_tool(argv, cwd, *, network=False, timeout=600, root=ROOT):
    result = subprocess.run(
        [str(item) for item in argv],
        cwd=cwd,
        env=environment(root, network=network),
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return result


def invoke(argv, cwd, *, network=False, timeout=600):
    result = run_tool(argv, cwd, network=network, timeout=timeout)
    if result.returncode:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        raise GuardError(f"{Path(str(argv[0])).name} exited {result.returncode}")
    return result.stdout


def initialize(update_lock=False):
    preflight()
    from quality import locks

    if not update_lock:
        locks()
    tofu = ROOT / ".tools/bin/tofu"
    for stack in STACKS:
        cwd = ROOT / "stacks" / stack
        args = [tofu, "init", "-backend=false", "-input=false", "-no-color"]
        lock_path = cwd / ".terraform.lock.hcl"
        original = None
        if not update_lock:
            if not lock_path.is_file():
                raise GuardError("Missing committed provider lock; reviewed update required")
            original = lock_path.read_bytes()
            # Native readonly mode rejects the 1.13.1 predecessor migration shim.
            # Exact source/version and native checksum checks still apply. Fail
            # if native init changes even one byte of the reviewed lockfile.
        print(invoke(args, cwd, network=True), end="")
        if original is not None and lock_path.read_bytes() != original:
            raise GuardError("Provider lock changed during bootstrap; review required")
        if update_lock:
            print(
                invoke(
                    [
                        tofu,
                        "providers",
                        "lock",
                        "-platform=darwin_arm64",
                        "-platform=linux_amd64",
                        "-platform=linux_arm64",
                    ],
                    cwd,
                    network=True,
                ),
                end="",
            )
            # The 1.13.1 migration shim adds an unused predecessor-registry
            # entry during providers lock. Native init prunes unused entries;
            # it preserves the signed upstream hashes. Never rewrite hashes.
            print(
                invoke(
                    [tofu, "init", "-backend=false", "-input=false", "-no-color"],
                    cwd,
                    network=True,
                ),
                end="",
            )


def validate():
    preflight()
    for stack in STACKS:
        report = json.loads(
            invoke([ROOT / ".tools/bin/tofu", "validate", "-json"], ROOT / "stacks" / stack)
        )
        if report.get("valid") is not True or report.get("error_count") != 0:
            raise GuardError("Native schema validation failed: " + stack)
        print(
            f"{stack}: native schema validation passed; "
            f"{report.get('warning_count')} warning(s)"
        )


def lint():
    preflight()
    for directory in [*(ROOT / "modules").iterdir(), *(ROOT / "stacks").iterdir()]:
        if directory.is_dir() and not directory.name.startswith("."):
            print(
                invoke(
                    [ROOT / ".tools/bin/tflint", "--config=" + str(ROOT / ".tflint.hcl")],
                    directory,
                ),
                end="",
            )
    print("TFLint: five modules/roots passed with bundled recommended rules")


def tests():
    suites = preflight()
    reports = {}
    for stack in STACKS:
        result = run_tool(
            [ROOT / ".tools/bin/tofu", "test", "-json", "-verbose"], ROOT / "stacks" / stack
        )
        logs = private_directory(ROOT / ".runtime/mock-output")
        destination = bounded(ROOT, logs / (stack + ".jsonl"))
        destination.write_text(result.stdout)
        destination.chmod(0o600)
        errors = bounded(ROOT, logs / (stack + ".stderr"))
        errors.write_text(result.stderr)
        errors.chmod(0o600)
        if result.returncode:
            print(result.stdout[-20000:])
            print(result.stderr[-4000:], file=sys.stderr)
            raise GuardError("Native mock tests failed: " + stack)
        events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        summaries = [item for item in events if item.get("type") == "test_summary"]
        expected = sum(
            len(names)
            for path, names in suites.items()
            if path.startswith("stacks/" + stack + "/")
        )
        if len(summaries) != 1:
            raise GuardError("Missing native test summary")
        summary = summaries[0]["test_summary"]
        if (
            summary.get("failed") != 0
            or summary.get("skipped") != 0
            or summary.get("passed") != expected
        ):
            raise GuardError("Missing, skipped or failed native test cases")
        positive = set()
        for path in suites:
            if path.startswith("stacks/" + stack + "/"):
                for group in parse(ROOT / path)["run"]:
                    for name, settings in group.items():
                        if not settings.get("expect_failures"):
                            positive.add(name)
        plans = {
            item["@testrun"]: item["test_plan"]
            for item in events
            if item.get("type") == "test_plan" and item["@testrun"] in positive
        }
        if set(plans) != positive:
            raise GuardError("Missing actual successful plan for policy checks")
        policies = {name: check_plan(plan, stack) for name, plan in plans.items()}
        enabled = next(plan for plan in plans.values() if plan.get("resource_changes"))
        negative = negative_controls(enabled, stack)
        reports[stack] = {
            "native_summary": summary,
            "policy_plans": policies,
            "negative_policies": negative,
        }
        print(
            f"{stack}: {expected} actual mocked plans passed, "
            f"{len(plans)} policy plans accepted, "
            f"{len(negative)} unsafe mutations rejected; zero cloud resources created"
        )
    destination = bounded(ROOT, ROOT / ".runtime/mock-output/summary.json")
    destination.write_text(json.dumps(reports, indent=2) + "\n")
    destination.chmod(0o600)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "init",
            "lint",
            "validate",
            "test",
            "plan",
            "apply",
            "destroy",
            "integration",
            "teardown",
            "clean",
        ],
    )
    parser.add_argument(
        "--update-lock",
        action="store_true",
        help="Explicit reviewed provider-lock update; registry downloads only",
    )
    args = parser.parse_args()
    if args.command in {"plan", "apply", "destroy", "integration", "teardown"}:
        print(
            "BLOCKED: live/authenticated cloud operations are unauthorized. "
            "Use make test for explicit provider mocks.",
            file=sys.stderr,
        )
        return 3
    if args.command == "clean":
        print(
            "No cloud resources are created by supported tasks. "
            "Local ignored provider/tool caches are retained; no deletion performed."
        )
        return 0
    if args.update_lock and args.command != "init":
        raise GuardError("Lock update only applies to registry initialization")
    if args.command == "init":
        initialize(args.update_lock)
    elif args.command == "validate":
        validate()
    elif args.command == "lint":
        lint()
    else:
        tests()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Local IaC check failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
