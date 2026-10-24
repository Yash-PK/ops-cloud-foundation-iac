"""Negative regressions for the pre-tool boundary; these never invoke OpenTofu."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import guard
import iac

SAFE_CONFIG = """
terraform {
  required_version = "= 1.13.1"
  required_providers {
    aws = {
      source = "registry.terraform.io/hashicorp/aws"
      version = "= 6.68.0"
    }
  }
  backend "local" {}
}
provider "aws" { region = "us-east-1" }
"""
SAFE_TEST = """
mock_provider "aws" {}
run "safe" {
  command = plan
  plan_options { refresh = false }
  assert {
    condition = true
    error_message = "Synthetic structural fixture only."
  }
}
"""


class GuardFixture(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="iac-guard-unit-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        (self.root / "modules" / "fixture").mkdir(parents=True)
        for stack in ("foundation", "state-bootstrap"):
            directory = self.root / "stacks" / stack
            (directory / "tests").mkdir(parents=True)
            (directory / "main.tf").write_text(SAFE_CONFIG)
            (directory / "tests" / "safe.tftest.hcl").write_text(SAFE_TEST)
        self.config = self.root / "stacks" / "foundation" / "main.tf"
        self.suite = self.config.parent / "tests" / "safe.tftest.hcl"

    def test_safe_mock_plan_fixture_is_accepted(self):
        self.assertEqual(sum(map(len, guard.preflight(self.root).values())), 2)

    def test_missing_aliased_or_real_test_provider_is_rejected(self):
        variants = {
            "missing": SAFE_TEST.replace('mock_provider "aws" {}', ""),
            "aliased": SAFE_TEST.replace(
                'mock_provider "aws" {}', 'mock_provider "aws" { alias = "mock" }'
            ),
            "real": SAFE_TEST + '\nprovider "aws" { region = "us-east-1" }',
            "duplicate": SAFE_TEST + '\nmock_provider "aws" {}',
        }
        for label, content in variants.items():
            with self.subTest(label=label):
                self.suite.write_text(content)
                with self.assertRaises(guard.GuardError):
                    guard.preflight(self.root)

    def test_apply_refresh_target_and_run_overrides_are_rejected(self):
        variants = {
            "implicit_apply": SAFE_TEST.replace("command = plan", ""),
            "explicit_apply": SAFE_TEST.replace("command = plan", "command = apply"),
            "missing_refresh": SAFE_TEST.replace("plan_options { refresh = false }", ""),
            "refresh": SAFE_TEST.replace("refresh = false", "refresh = true"),
            "target": SAFE_TEST.replace(
                "refresh = false", "refresh = false\n target = [aws_vpc.fixture]"
            ),
            "replace": SAFE_TEST.replace(
                "refresh = false", "refresh = false\n replace = [aws_vpc.fixture]"
            ),
            "provider_override": SAFE_TEST.replace(
                "command = plan", "command = plan\n providers = { aws = aws.live }"
            ),
            "module_override": SAFE_TEST.replace(
                "command = plan", 'command = plan\n module { source = "../other" }'
            ),
            "no_assertion": SAFE_TEST[: SAFE_TEST.index("  assert {")] + "}\n",
        }
        for label, content in variants.items():
            with self.subTest(label=label):
                self.suite.write_text(content)
                with self.assertRaises(guard.GuardError):
                    guard.preflight(self.root)

    def test_cloud_hooks_data_and_unreviewed_sources_are_rejected(self):
        variants = {
            "provisioner": (
                'resource "aws_instance" "bad" { provisioner "local-exec" '
                '{ command = "never-run" } }'
            ),
            "connection": 'resource "aws_instance" "bad" { connection { host = "192.0.2.1" } }',
            "data": 'data "aws_caller_identity" "bad" {}',
            "external": 'data "external" "bad" { program = ["never-run"] }',
            "remote_module": 'module "bad" { source = "example.invalid/unreviewed/module" }',
            "escaping_module": 'module "bad" { source = "../../../outside" }',
            "remote_backend": 'terraform { backend "s3" { bucket = "mock-bucket" } }',
            "credential": 'provider "aws" { access_key = "SYNTHETIC-NOT-A-CREDENTIAL" }',
            "endpoint": 'provider "aws" { endpoints { sts = "https://example.invalid" } }',
            "foreign_provider": 'provider "external" {}',
            "foreign_resource": 'resource "null_resource" "bad" {}',
            "file_read": 'output "bad" { value = file("/nonexistent/synthetic-fixture") }',
            "file_read_in_list": (
                'output "bad" { value = [file("/nonexistent/synthetic-fixture")] }'
            ),
            "template_read": (
                'output "bad" { value = templatefile("/nonexistent/synthetic-fixture", {}) }'
            ),
        }
        for label, content in variants.items():
            with self.subTest(label=label):
                self.config.write_text(SAFE_CONFIG + content)
                with self.assertRaises(guard.GuardError):
                    guard.preflight(self.root)

    def test_test_variables_cannot_read_host_files(self):
        for content in (
            SAFE_TEST + '\nvariables { ami_id = file("/nonexistent/synthetic-fixture") }',
            SAFE_TEST.replace(
                "command = plan",
                "command = plan\n variables { "
                'ami_id = file("/nonexistent/synthetic-fixture") }',
            ),
        ):
            with self.subTest(source=content):
                self.suite.write_text(content)
                with self.assertRaises(guard.GuardError):
                    guard.preflight(self.root)

    def test_all_file_hash_and_listing_functions_are_rejected_in_nested_values(self):
        calls = [
            f'{function}("/nonexistent/synthetic-fixture")'
            for function in (
                "file",
                "filebase64",
                "fileexists",
                "filemd5",
                "filesha1",
                "filesha256",
                "filesha512",
                "filebase64sha256",
                "filebase64sha512",
            )
        ] + [
            'fileset("/nonexistent/synthetic-fixture", "*")',
            'templatefile("/nonexistent/synthetic-fixture", {})',
        ]
        for call in calls:
            with self.subTest(call=call):
                self.config.write_text(SAFE_CONFIG + f'\noutput "bad" {{ value = [[{call}]] }}')
                with self.assertRaises(guard.GuardError):
                    guard.preflight(self.root)
                self.config.write_text(SAFE_CONFIG)
                self.suite.write_text(SAFE_TEST + f"\nvariables {{ fixture = [[{call}]] }}")
                with self.assertRaises(guard.GuardError):
                    guard.preflight(self.root)
                self.suite.write_text(SAFE_TEST)

    def test_expression_object_keys_and_provider_functions_are_rejected(self):
        expressions = [
            '{ (file("/nonexistent/synthetic-fixture")) = "value" }',
            '[provider::aws::arn_parse("synthetic-fixture")]',
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                self.config.write_text(
                    SAFE_CONFIG + f'\noutput "bad" {{ value = {expression} }}'
                )
                with self.assertRaises(guard.GuardError):
                    guard.preflight(self.root)
                self.config.write_text(SAFE_CONFIG)
                self.suite.write_text(SAFE_TEST + f"\nvariables {{ fixture = {expression} }}")
                with self.assertRaises(guard.GuardError):
                    guard.preflight(self.root)
                self.suite.write_text(SAFE_TEST)

    def test_provider_drift_and_nonexact_constraints_are_rejected(self):
        for replacement in ("~> 6.68.0", ">= 6.68.0", "6.67.0"):
            with self.subTest(replacement=replacement):
                self.config.write_text(SAFE_CONFIG.replace("= 6.68.0", replacement))
                with self.assertRaises(guard.GuardError):
                    guard.preflight(self.root)
        self.config.write_text(
            SAFE_CONFIG.replace(
                "registry.terraform.io/hashicorp/aws", "example.invalid/hashicorp/aws"
            )
        )
        with self.assertRaises(guard.GuardError):
            guard.preflight(self.root)

    def test_shadow_state_override_and_variable_files_are_rejected(self):
        filenames = (
            "shadow.tofu",
            "shadow.tofu.json",
            "shadow.tf.json",
            "shadow.tftest.json",
            "shadow.tofutest.hcl",
            "shadow.tofutest.json",
            "terraform.tfstate",
            "terraform.tfstate.backup",
            "override.tf",
            "danger_override.tf",
            "terraform.tfvars",
            "danger.auto.tfvars",
            "danger.auto.tfvars.json",
        )
        for filename in filenames:
            with self.subTest(filename=filename):
                path = self.config.parent / filename
                path.write_text("{}")
                try:
                    with self.assertRaises(guard.GuardError):
                        guard.preflight(self.root)
                finally:
                    path.unlink()

    def test_symlink_is_rejected_without_following_target(self):
        target = self.root / "outside.txt"
        target.write_text("synthetic fixture")
        link = self.config.parent / "linked.tf"
        link.symlink_to(target)
        with self.assertRaises(guard.GuardError):
            guard.preflight(self.root)
        with self.assertRaises(guard.GuardError):
            guard.parse(link)

    def test_local_module_cannot_hide_source_inside_ignored_tool_cache(self):
        hidden = self.root / "modules" / ".terraform" / "hidden"
        hidden.mkdir(parents=True)
        (hidden / "main.tf").write_text(
            'output "bad" { value = file("/nonexistent/synthetic-fixture") }'
        )
        self.config.write_text(
            SAFE_CONFIG + '\nmodule "hidden" { source = "../../modules/.terraform/hidden" }'
        )
        with self.assertRaises(guard.GuardError):
            guard.preflight(self.root)

    def test_malformed_oversize_and_nonfile_hcl_are_rejected(self):
        for source in ('resource "aws_vpc" {', "#" * 150_001):
            with self.subTest(size=len(source)):
                self.config.write_text(source)
                with self.assertRaises(guard.GuardError):
                    guard.parse(self.config)
        with self.assertRaises(guard.GuardError):
            guard.parse(self.config.parent)


class ExecutionBoundary(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="iac-env-unit-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()

    def test_environment_never_inherits_canary_credentials_or_cli_arguments(self):
        synthetic = {
            "AWS_ACCESS_KEY_ID": "SYNTHETIC-CANARY-ACCESS",
            "AWS_SECRET_ACCESS_KEY": "SYNTHETIC-CANARY-SECRET",
            "AWS_SESSION_TOKEN": "SYNTHETIC-CANARY-TOKEN",
            "AWS_PROFILE": "SYNTHETIC-CANARY-PROFILE",
            "TF_CLI_ARGS": "SYNTHETIC-CANARY-ARGUMENTS",
            "TF_VAR_enable": "true",
            "HOME": "/nonexistent/synthetic-user-home",
            "HTTPS_PROXY": "http://example.invalid:9999",
        }
        with mock.patch.object(os, "environ", synthetic):
            result = iac.environment(self.root)
        self.assertFalse(set(synthetic).difference({"HOME", "HTTPS_PROXY"}) & result.keys())
        self.assertFalse(any("CANARY" in value for value in result.values()))
        self.assertEqual(result["HOME"], str(self.root / ".runtime" / "empty-home"))
        self.assertEqual(result["AWS_EC2_METADATA_DISABLED"], "true")
        for name in ("AWS_CONFIG_FILE", "AWS_SHARED_CREDENTIALS_FILE"):
            self.assertTrue(Path(result[name]).is_relative_to(self.root / ".runtime"))
            self.assertEqual(Path(result[name]).read_text(), "")
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
            self.assertEqual(result[name], "http://127.0.0.1:9")
        self.assertEqual(result["NO_PROXY"], "")

    def test_network_initialization_still_uses_empty_credentials(self):
        result = iac.environment(self.root, network=True)
        self.assertFalse({"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"} & result.keys())
        self.assertEqual(result["AWS_EC2_METADATA_DISABLED"], "true")
        self.assertTrue(Path(result["HOME"]).is_relative_to(self.root))
        self.assertNotIn("AWS_ACCESS_KEY_ID", result)
        self.assertNotIn("AWS_PROFILE", result)

    def test_live_operations_stop_before_any_tool_process(self):
        for operation in ("plan", "apply", "destroy", "integration", "teardown"):
            with (
                self.subTest(operation=operation),
                mock.patch.object(sys, "argv", ["iac.py", operation]),
            ):
                with (
                    mock.patch.object(iac, "run_tool") as runner,
                    contextlib.redirect_stderr(io.StringIO()) as errors,
                ):
                    self.assertEqual(iac.main(), 3)
                    runner.assert_not_called()
                    self.assertIn("BLOCKED", errors.getvalue())

    def test_unknown_operation_is_rejected_before_any_tool_process(self):
        with mock.patch.object(sys, "argv", ["iac.py", "import"]):
            with (
                mock.patch.object(iac, "run_tool") as runner,
                contextlib.redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as error:
                    iac.main()
                self.assertNotEqual(error.exception.code, 0)
                runner.assert_not_called()

    def test_validate_never_requests_network(self):
        with (
            mock.patch.object(iac, "preflight", return_value={}),
            mock.patch.object(iac, "STACKS", ("foundation",)),
        ):
            with mock.patch.object(
                iac, "invoke", return_value='{"valid":true,"error_count":0,"warning_count":0}'
            ) as invoke:
                with contextlib.redirect_stdout(io.StringIO()):
                    iac.validate()
                self.assertNotIn("network", invoke.call_args.kwargs)
                self.assertEqual(invoke.call_args.args[0][1:3], ["validate", "-json"])

    def test_mock_test_phase_never_requests_network(self):
        suites = {"stacks/foundation/tests/safe.tftest.hcl": ["safe"]}
        event = (
            "\n".join(
                json.dumps(item)
                for item in [
                    {
                        "type": "test_summary",
                        "test_summary": {"passed": 1, "failed": 0, "skipped": 0},
                    },
                    {
                        "type": "test_plan",
                        "@testrun": "safe",
                        "test_plan": {"resource_changes": [{"synthetic_fixture": True}]},
                    },
                ]
            )
            + "\n"
        )
        result = mock.Mock(returncode=0, stdout=event, stderr="")

        def create_fixture_directory(path):
            path.mkdir(parents=True, exist_ok=True)
            return path

        with (
            mock.patch.object(iac, "ROOT", self.root),
            mock.patch.object(iac, "STACKS", ("foundation",)),
        ):
            with (
                mock.patch.object(iac, "preflight", return_value=suites),
                mock.patch.object(
                    iac, "private_directory", side_effect=create_fixture_directory
                ),
            ):
                with (
                    mock.patch.object(
                        iac, "parse", return_value={"run": [{"safe": {"command": "plan"}}]}
                    ),
                    mock.patch.object(iac, "check_plan", return_value={"resources": 1}),
                    mock.patch.object(
                        iac,
                        "negative_controls",
                        return_value=[{"name": "synthetic-control", "rejected": True}],
                    ),
                ):
                    with (
                        mock.patch.object(iac, "run_tool", return_value=result) as runner,
                        contextlib.redirect_stdout(io.StringIO()),
                    ):
                        report = iac.tests()["foundation"]
                        self.assertEqual(report["native_summary"]["passed"], 1)
                        self.assertEqual(report["policy_plans"], {"safe": {"resources": 1}})
                        self.assertNotIn("network", runner.call_args.kwargs)
                        self.assertEqual(
                            runner.call_args.args[0][1:], ["test", "-json", "-verbose"]
                        )

    def test_only_registry_initialization_requests_network(self):
        with (
            mock.patch.object(iac, "ROOT", self.root),
            mock.patch.object(iac, "STACKS", ("foundation",)),
        ):
            with (
                mock.patch.object(iac, "preflight"),
                mock.patch.object(iac, "invoke", return_value="") as invoke,
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    iac.initialize(update_lock=True)
                self.assertEqual(invoke.call_count, 3)
                self.assertTrue(
                    all(call.kwargs.get("network") is True for call in invoke.call_args_list)
                )
                self.assertIn("-backend=false", invoke.call_args_list[0].args[0])
                self.assertEqual(invoke.call_args_list[1].args[0][1:3], ["providers", "lock"])
                self.assertIn("-backend=false", invoke.call_args_list[2].args[0])


if __name__ == "__main__":
    unittest.main()
