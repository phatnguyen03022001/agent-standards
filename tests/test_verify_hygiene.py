import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "tools" / "verify.py"


class VerifyHygieneTests(unittest.TestCase):
    def _workspace(self, validator_source, test_source):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "tools").mkdir()
        (root / "tests").mkdir()
        shutil.copy2(VERIFY, root / "tools" / "verify.py")
        (root / "tools" / "validate.py").write_text(validator_source, encoding="utf-8")
        (root / "tests" / "test_probe.py").write_text(test_source, encoding="utf-8")
        return td, root

    @staticmethod
    def _cache_artifacts(root):
        return sorted(
            str(path.relative_to(root))
            for path in root.rglob("*")
            if (path.is_dir() and path.name == "__pycache__")
            or (path.is_file() and path.suffix in {".pyc", ".pyo"})
        )

    def test_runner_uses_current_interpreter_with_no_bytecode_and_leaves_no_cache(self):
        validator = """\
import json
import os
import sys
from pathlib import Path
Path(os.environ[\"TRACE\"]).open(\"a\", encoding=\"utf-8\").write(json.dumps({\"kind\": \"validator\", \"executable\": sys.executable, \"dont_write_bytecode\": sys.dont_write_bytecode}) + \"\\n\")
print(\"VALIDATOR_OK\")
"""
        test_module = """\
import json
import os
import sys
import unittest
from pathlib import Path

class Probe(unittest.TestCase):
    def test_probe(self):
        Path(os.environ[\"TRACE\"]).open(\"a\", encoding=\"utf-8\").write(json.dumps({\"kind\": \"unittest\", \"executable\": sys.executable, \"dont_write_bytecode\": sys.dont_write_bytecode}) + \"\\n\")
        self.assertTrue(True)
"""
        td, root = self._workspace(validator, test_module)
        try:
            trace = root / "trace.jsonl"
            env = dict(os.environ, TRACE=str(trace))
            completed = subprocess.run(
                [sys.executable, str(root / "tools" / "verify.py")],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            records = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(["validator", "unittest"], [record["kind"] for record in records])
            for record in records:
                self.assertEqual(sys.executable, record["executable"])
                self.assertTrue(record["dont_write_bytecode"])
            self.assertEqual([], self._cache_artifacts(root))
        finally:
            td.cleanup()

    def test_runner_leaves_exact_tracked_copy_clean_without_cleanup(self):
        if sys.dont_write_bytecode:
            return

        listed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout.split(b"\0")
        tracked = [Path(item.decode("utf-8")) for item in listed if item]

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for relative in tracked:
                source = ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            subprocess.run(
                ["git", "-c", "user.name=Executor", "-c", "user.email=executor@example.invalid",
                 "commit", "-qm", "exact-final snapshot"],
                cwd=root,
                check=True,
            )
            self.assertEqual([], self._cache_artifacts(root))

            completed = subprocess.run(
                [sys.executable, str(root / "tools" / "verify.py")],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            self.assertIn("VALID: standards definition", completed.stdout)
            self.assertEqual([], self._cache_artifacts(root))
            status = subprocess.run(
                ["git", "status", "--porcelain=v1"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertEqual("", status.stdout)

    def test_runner_propagates_validator_failure_and_stops(self):
        validator = """\
import sys
print(\"EXPECTED_VALIDATOR_FAILURE\", file=sys.stderr)
raise SystemExit(7)
"""
        test_module = """\
import os
import unittest
from pathlib import Path

class Probe(unittest.TestCase):
    def test_should_not_run(self):
        Path(os.environ[\"SENTINEL\"]).write_text(\"ran\", encoding=\"utf-8\")
"""
        td, root = self._workspace(validator, test_module)
        try:
            sentinel = root / "unittest-ran"
            env = dict(os.environ, SENTINEL=str(sentinel))
            completed = subprocess.run(
                [sys.executable, str(root / "tools" / "verify.py")],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(7, completed.returncode, completed.stdout + completed.stderr)
            self.assertIn("EXPECTED_VALIDATOR_FAILURE", completed.stderr)
            self.assertFalse(sentinel.exists())
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
