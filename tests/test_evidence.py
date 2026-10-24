"""Evidence validation edges using explicitly synthetic reports, never Git or cloud."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evidence

FINGERPRINT = "0" * 64


def command(target):
    return {
        "argv": ["make", target],
        "exit_code": 0,
        "timed_out": False,
        "output": "Synthetic unit fixture, not execution evidence.",
    }


def clean_clone_report():
    return {
        "profile": "clean-clone",
        "passed": True,
        "clean_at_start": True,
        "code_fingerprint": FINGERPRINT,
        "revision": "0" * 40,
        "started_at": "2026-10-08T00:00:00+00:00",
        "finished_at": "2026-10-08T00:00:01+00:00",
        "commands": [
            command(target)
            for target in ("bootstrap", "doctor", "validate", "demo", "security")
        ],
        "not_run": [],
        "temporary_clone_removed": True,
        "assertions": [
            {"name": "clone_revision_matches_source", "passed": True},
            {"name": "clone_remains_clean_after_checks", "passed": True},
        ],
    }


class EvidenceCommands(unittest.TestCase):
    def test_command_success_requires_zero_integer_exit_and_complete_output(self):
        self.assertTrue(evidence.commands_passed([command("validate")]))
        for field, value in (
            ("exit_code", False),
            ("exit_code", True),
            ("exit_code", "0"),
            ("exit_code", 1),
            ("exit_code", -1),
            ("timed_out", True),
            ("timed_out", None),
            ("output", None),
        ):
            with self.subTest(field=field, value=value):
                entry = command("validate")
                entry[field] = value
                self.assertFalse(evidence.commands_passed([entry]))
        for value in (None, [], {}, "passed", [None]):
            with self.subTest(value=value):
                self.assertFalse(evidence.commands_passed(value))

    def test_one_failed_or_timed_out_command_invalidates_the_batch(self):
        for field, value in (("exit_code", 3), ("timed_out", True)):
            with self.subTest(field=field):
                entries = [command("doctor"), command("validate")]
                entries[1][field] = value
                self.assertFalse(evidence.commands_passed(entries))


class EvidenceReports(unittest.TestCase):
    def assert_invalid(self, report):
        self.assertFalse(evidence.valid_report(report, "clean-clone", FINGERPRINT))

    def test_complete_synthetic_clone_shape_is_accepted_by_shape_helper_only(self):
        # valid_report does not prove revision ancestry or execute commands;
        # evidence.main performs the separate fingerprint/ancestry checks.
        self.assertTrue(evidence.valid_report(clean_clone_report(), "clean-clone", FINGERPRINT))

    def test_stale_dirty_incomplete_or_failed_report_is_rejected(self):
        for field, value in (
            ("profile", "controller"),
            ("passed", False),
            ("passed", 1),
            ("clean_at_start", False),
            ("code_fingerprint", "1" * 64),
            ("revision", "not-a-revision"),
            ("started_at", ""),
            ("finished_at", ""),
            ("not_run", ["validate"]),
            ("temporary_clone_removed", False),
        ):
            with self.subTest(field=field, value=value):
                report = clean_clone_report()
                report[field] = value
                self.assert_invalid(report)

    def test_missing_or_failed_clone_assertion_is_rejected(self):
        report = clean_clone_report()
        report["assertions"].pop()
        self.assert_invalid(report)
        report = clean_clone_report()
        report["assertions"][1]["passed"] = False
        self.assert_invalid(report)

    def test_missing_reordered_or_failed_required_command_is_rejected(self):
        missing = clean_clone_report()
        missing["commands"].pop()
        reordered = clean_clone_report()
        reordered["commands"].reverse()
        failed = clean_clone_report()
        failed["commands"][2]["exit_code"] = 1
        for report in (missing, reordered, failed):
            with self.subTest(report=report):
                self.assert_invalid(report)

    def test_unknown_profile_or_nondictionary_report_is_rejected(self):
        self.assertFalse(evidence.valid_report(clean_clone_report(), "unknown", FINGERPRINT))
        for value in (None, [], "passed", True):
            with self.subTest(value=value):
                self.assert_invalid(value)

    def test_validation_does_not_rewrite_the_evidence(self):
        report = clean_clone_report()
        original = copy.deepcopy(report)
        evidence.valid_report(report, "clean-clone", FINGERPRINT)
        self.assertEqual(report, original)


if __name__ == "__main__":
    unittest.main()
