"""Policy helper and fail-closed tests with small synthetic inputs.

Security acceptance and mutation controls use real native mock-plan events in
scripts/iac.py. These unit tests do not substitute handwritten resource plans
for that integration gate, and require no .runtime artifacts.
"""

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import policy


def disabled_plan():
    return {
        "format_version": "1.2",
        "variables": {"enable": {"value": False}},
        "resource_changes": [],
    }


def partial_enabled_plan(resource):
    """Incomplete by design: exercise early rejection, never a valid fixture."""
    return {
        "format_version": "1.2",
        "variables": {
            "enable": {"value": True},
            "enable_public_edge": {"value": False},
            "owner": {"value": "synthetic-owner"},
            "project": {"value": "synthetic-project"},
            "environment": {"value": "lab"},
        },
        "resource_changes": [resource],
    }


class PlanBoundary(unittest.TestCase):
    def test_default_disabled_profiles_have_zero_changes(self):
        for stack in ("foundation", "state-bootstrap"):
            with self.subTest(stack=stack):
                self.assertEqual(
                    policy.check_plan(disabled_plan(), stack),
                    {"resources": 0, "profile": stack},
                )

    def test_disabled_profile_rejects_any_resource_change(self):
        plan = disabled_plan()
        plan["resource_changes"] = [{"change": {"actions": ["create"]}}]
        with self.assertRaises(policy.PolicyError):
            policy.check_plan(plan, "foundation")

    def test_unknown_profile_is_rejected_even_when_disabled(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                plan = disabled_plan()
                plan["variables"]["enable"]["value"] = enabled
                with self.assertRaises(policy.PolicyError):
                    policy.check_plan(plan, "unreviewed-stack")

    def test_malformed_plan_shapes_are_policy_errors(self):
        invalid = [None, [], "not-a-plan", 17, {}, {"format_version": "1.1"}]
        for variables in (None, [], "not-variables", {"enable": {}}):
            invalid.append({"format_version": "1.2", "variables": variables})
        for enabled in (None, "false", 0, 1, [], {}):
            plan = disabled_plan()
            plan["variables"]["enable"]["value"] = enabled
            invalid.append(plan)
        for plan in invalid:
            with self.subTest(plan=plan), self.assertRaises(policy.PolicyError):
                policy.check_plan(plan, "foundation")

    def test_enabled_plan_requires_complete_resource_set(self):
        plan = disabled_plan()
        plan["variables"]["enable"]["value"] = True
        plan["variables"]["enable_public_edge"] = {"value": False}
        with self.assertRaises(policy.PolicyError):
            policy.check_plan(plan, "foundation")

    def test_provider_mode_and_noncreation_actions_fail_before_profile_checks(self):
        resource = {
            "type": "aws_vpc",
            "mode": "managed",
            "provider_name": "registry.terraform.io/hashicorp/aws",
            "change": {"actions": ["create"], "after": {}},
        }
        variants = [
            ("mode", "data"),
            ("provider_name", "example.invalid/unreviewed/provider"),
            ("change", {"actions": ["delete"], "after": {}}),
            ("change", {"actions": ["update"], "after": {}}),
            ("change", {"actions": ["delete", "create"], "after": {}}),
            ("change", {"actions": ["create"], "after": None}),
        ]
        for field, value in variants:
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(resource)
                changed[field] = value
                with self.assertRaises(policy.PolicyError):
                    policy.check_plan(partial_enabled_plan(changed), "foundation")

    def test_negative_controls_reject_disabled_or_malformed_input(self):
        for plan in ({}, disabled_plan()):
            with self.subTest(plan=plan), self.assertRaises(policy.PolicyError):
                policy.negative_controls(plan, "foundation")

    def test_negative_controls_report_if_a_mutation_is_accepted(self):
        # Exercise only the control harness's fail-closed behavior. Production
        # acceptance/mutations are separately checked against actual native plans.
        partial = {"resource_changes": [{"type": "aws_instance", "change": {"after": {}}}]}
        original = copy.deepcopy(partial)
        with mock.patch.object(policy, "check_plan", return_value={"resources": 1}):
            with self.assertRaisesRegex(policy.PolicyError, "Negative policy control accepted"):
                policy.negative_controls(partial, "foundation")
        self.assertEqual(partial, original, "Mutation controls must leave their input intact")


class PolicyDocuments(unittest.TestCase):
    def test_single_security_block_requires_exactly_one_list_item(self):
        sentinel = {"synthetic": True}
        self.assertIs(policy.one([sentinel]), sentinel)
        for invalid in (None, {}, "item", [], [sentinel, sentinel]):
            with self.subTest(invalid=invalid), self.assertRaises(policy.PolicyError):
                policy.one(invalid)

    def test_document_accepts_standard_policy_shape(self):
        statement = {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Principal": {"Service": "ec2.amazonaws.com"},
        }
        self.assertEqual(
            policy.document(json.dumps({"Version": "2012-10-17", "Statement": [statement]})),
            [statement],
        )

    def test_malformed_json_and_statement_shapes_are_policy_errors(self):
        invalid = [
            "not-json",
            "null",
            "[]",
            "true",
            "17",
            "{}",
            '{"Version":"2008-10-17","Statement":[{}]}',
            '{"Version":"2012-10-17","Statement":[]}',
            '{"Version":"2012-10-17","Statement":{}}',
            '{"Version":"2012-10-17","Statement":[null]}',
            '{"Version":"2012-10-17","Statement":["invalid"]}',
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(policy.PolicyError):
                policy.document(value)

    def test_named_role_arn_rejects_principal_wildcards_and_other_identity_types(self):
        self.assertTrue(policy.role_arn("arn:aws:iam::000000000000:role/mock-state-admin"))
        for value in (
            None,
            "*",
            "arn:aws:iam::*:role/mock-state-admin",
            "arn:aws:iam::000000000000:role/*",
            "arn:aws:iam::000000000000:user/mock-user",
            "arn:aws:iam::000000000000:root",
            "arn:aws:iam::0000:role/mock-role",
            "arn:aws-cn:iam::000000000000:role/mock-role",
        ):
            with self.subTest(value=value):
                self.assertFalse(policy.role_arn(value))


if __name__ == "__main__":
    unittest.main()
