"""Regression: repair a broken local interpreter without losing its environment."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bootstrap


class EnvironmentRepair(unittest.TestCase):
    def test_broken_environment_is_preserved_before_recreation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / ".python-version").write_text("3.14.8\n")
            target = root / ".venv"
            (target / "bin").mkdir(parents=True)
            (target / "bin/python").write_text("broken launcher")
            (target / "keep.txt").write_text("existing environment contents")

            def create(destination):
                self.assertFalse(destination.exists())
                (destination / "bin").mkdir(parents=True)
                (destination / "bin/python").write_text("replacement launcher")

            with (
                patch.object(bootstrap, "ROOT", root),
                patch.object(
                    bootstrap,
                    "private_directory",
                    side_effect=lambda path: path.mkdir(parents=True) or path,
                ),
                patch.object(bootstrap.venv, "EnvBuilder") as builder,
                patch.object(bootstrap.subprocess, "run") as run,
            ):
                run.side_effect = [
                    subprocess.CompletedProcess([], -6, stdout="", stderr="missing framework"),
                    subprocess.CompletedProcess([], 0),
                ]
                builder.return_value.create.side_effect = create
                bootstrap.prepare_environment(target)
            backups = list((root / ".runtime/venv-backups").iterdir())
            self.assertEqual(len(backups), 1)
            self.assertEqual(
                (backups[0] / "keep.txt").read_text(), "existing environment contents"
            )
            self.assertEqual((target / "bin/python").read_text(), "replacement launcher")

    def test_certificate_fix_failure_stops_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "bin").mkdir()
            (target / "bin/python").touch()
            expected = (bootstrap.ROOT / ".python-version").read_text().strip()
            with (
                patch.object(bootstrap.venv, "EnvBuilder") as builder,
                patch.object(bootstrap.subprocess, "run") as run,
            ):
                run.side_effect = [
                    subprocess.CompletedProcess([], 0, stdout=expected),
                    subprocess.CalledProcessError(1, ["pip"]),
                ]
                with self.assertRaises(subprocess.CalledProcessError):
                    bootstrap.prepare_environment(target)
                builder.assert_not_called()


if __name__ == "__main__":
    unittest.main()
