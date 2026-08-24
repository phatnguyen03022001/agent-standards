import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate", ROOT / "tools" / "validate.py")
validate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate)


class ValidatorTests(unittest.TestCase):
    def test_candidate_definition_passes(self):
        self.assertTrue(validate.validate(ROOT))

    def _copy_tree(self):
        td = tempfile.TemporaryDirectory()
        dst = Path(td.name)
        (dst / "standards").mkdir()
        for src in (ROOT / "standards").glob("*.yaml"):
            (dst / "standards" / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        return td, dst

    def test_duplicate_yaml_key_rejected(self):
        td, dst = self._copy_tree()
        try:
            p = dst / "standards" / "correctness.yaml"
            p.write_text("dimension: COR\ndimension: COR\napplicability: {mode: always}\nrequirements: []\n", encoding="utf-8")
            with self.assertRaises(validate.ValidationError):
                validate.validate(dst)
        finally:
            td.cleanup()

    def test_alias_rejected(self):
        td, dst = self._copy_tree()
        try:
            p = dst / "standards" / "correctness.yaml"
            p.write_text("dimension: COR\napplicability: &a {mode: always}\nrequirements: *a\n", encoding="utf-8")
            with self.assertRaises(validate.ValidationError):
                validate.validate(dst)
        finally:
            td.cleanup()

    def test_id_level_mismatch_rejected(self):
        td, dst = self._copy_tree()
        try:
            p = dst / "standards" / "correctness.yaml"
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            data["requirements"][0]["level"] = 2
            p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            with self.assertRaises(validate.ValidationError):
                validate.validate(dst)
        finally:
            td.cleanup()

    def test_unknown_requirement_field_rejected(self):
        td, dst = self._copy_tree()
        try:
            p = dst / "standards" / "correctness.yaml"
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            data["requirements"][0]["vendor"] = "example"
            p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            with self.assertRaises(validate.ValidationError):
                validate.validate(dst)
        finally:
            td.cleanup()

    def test_duplicate_statement_rejected(self):
        td, dst = self._copy_tree()
        try:
            p = dst / "standards" / "correctness.yaml"
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            data["requirements"][1]["statement"] = data["requirements"][0]["statement"]
            p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            with self.assertRaises(validate.ValidationError):
                validate.validate(dst)
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
