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
    def _copy_tree(self):
        td = tempfile.TemporaryDirectory()
        dst = Path(td.name)
        (dst / "standards").mkdir()
        for src in (ROOT / "standards").glob("*.yaml"):
            (dst / "standards" / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        return td, dst

    def _load(self, dst, filename):
        p = dst / "standards" / filename
        return p, yaml.safe_load(p.read_text(encoding="utf-8"))

    def _write(self, path, data):
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

    def _assert_invalid(self, dst, contains=None):
        with self.assertRaises(validate.ValidationError) as cm:
            validate.validate(dst)
        if contains is not None:
            self.assertIn(contains, str(cm.exception))

    def test_valid_candidate_definition(self):
        self.assertTrue(validate.validate(ROOT))

    def test_duplicate_yaml_key_rejected(self):
        td, dst = self._copy_tree()
        try:
            p = dst / "standards" / "correctness.yaml"
            p.write_text("dimension: COR\ndimension: COR\napplicability: {mode: always}\nrequirements: []\n", encoding="utf-8")
            self._assert_invalid(dst, "duplicate YAML mapping key")
        finally:
            td.cleanup()

    def test_unhashable_yaml_mapping_key_is_controlled(self):
        td, dst = self._copy_tree()
        try:
            p = dst / "standards" / "correctness.yaml"
            p.write_text("? [not, scalar]\n: value\n", encoding="utf-8")
            self._assert_invalid(dst, "YAML mapping key must be hashable scalar")
        finally:
            td.cleanup()

    def test_yaml_anchor_alias_rejected(self):
        td, dst = self._copy_tree()
        try:
            p = dst / "standards" / "correctness.yaml"
            p.write_text("dimension: COR\napplicability: &a {mode: always}\nrequirements: *a\n", encoding="utf-8")
            self._assert_invalid(dst, "anchors/aliases are forbidden")
        finally:
            td.cleanup()

    def test_custom_yaml_tag_rejected(self):
        td, dst = self._copy_tree()
        try:
            p = dst / "standards" / "correctness.yaml"
            p.write_text("dimension: !custom COR\napplicability: {mode: always}\nrequirements: []\n", encoding="utf-8")
            self._assert_invalid(dst, "custom YAML tag forbidden")
        finally:
            td.cleanup()

    def test_malformed_yaml_rejected(self):
        td, dst = self._copy_tree()
        try:
            p = dst / "standards" / "correctness.yaml"
            p.write_text("dimension: COR\napplicability: [\n", encoding="utf-8")
            self._assert_invalid(dst, "malformed YAML")
        finally:
            td.cleanup()

    def test_generation_exact_type_and_value(self):
        for value in (1.0, True, "1", 2):
            with self.subTest(value=value):
                td, dst = self._copy_tree()
                try:
                    p, data = self._load(dst, "manifest.yaml")
                    data["generation"] = value
                    self._write(p, data)
                    self._assert_invalid(dst, "manifest.generation must be exactly integer 1")
                finally:
                    td.cleanup()

    def test_manifest_dimension_object_type_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "manifest.yaml")
            data["dimensions"][0] = ["COR"]
            self._write(p, data)
            self._assert_invalid(dst, "expected mapping")
        finally:
            td.cleanup()

    def test_manifest_dimension_field_type_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "manifest.yaml")
            data["dimensions"][0]["file"] = ["correctness.yaml"]
            self._write(p, data)
            self._assert_invalid(dst, "expected nonempty string")
        finally:
            td.cleanup()

    def test_duplicate_dimension_code_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "manifest.yaml")
            data["dimensions"][1]["code"] = data["dimensions"][0]["code"]
            self._write(p, data)
            self._assert_invalid(dst, "duplicate dimension code")
        finally:
            td.cleanup()

    def test_duplicate_dimension_key_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "manifest.yaml")
            data["dimensions"][1]["key"] = data["dimensions"][0]["key"]
            self._write(p, data)
            self._assert_invalid(dst, "duplicate dimension key")
        finally:
            td.cleanup()

    def test_duplicate_filename_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "manifest.yaml")
            data["dimensions"][1]["file"] = data["dimensions"][0]["file"]
            self._write(p, data)
            self._assert_invalid(dst, "duplicate dimension filename")
        finally:
            td.cleanup()

    def test_registry_code_order_mismatch_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "manifest.yaml")
            data["dimensions"][0], data["dimensions"][1] = data["dimensions"][1], data["dimensions"][0]
            self._write(p, data)
            self._assert_invalid(dst, "dimension registry code/order mismatch")
        finally:
            td.cleanup()

    def test_declared_file_missing_rejected(self):
        td, dst = self._copy_tree()
        try:
            (dst / "standards" / "correctness.yaml").unlink()
            self._assert_invalid(dst, "standard file registry mismatch")
        finally:
            td.cleanup()

    def test_undeclared_standards_file_rejected(self):
        td, dst = self._copy_tree()
        try:
            (dst / "standards" / "extra.yaml").write_text("dimension: XXX\n", encoding="utf-8")
            self._assert_invalid(dst, "standard file registry mismatch")
        finally:
            td.cleanup()

    def test_requirement_id_syntax_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["id"] = "COR-1-2"
            self._write(p, data)
            self._assert_invalid(dst, "invalid ID syntax")
        finally:
            td.cleanup()

    def test_requirement_id_type_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["id"] = ["COR-1.2"]
            self._write(p, data)
            self._assert_invalid(dst, "invalid id/level type")
        finally:
            td.cleanup()

    def test_id_dimension_prefix_mismatch_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["id"] = "SEC-1.2"
            self._write(p, data)
            self._assert_invalid(dst, "ID dimension prefix mismatch")
        finally:
            td.cleanup()

    def test_id_level_mismatch_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["level"] = 2
            self._write(p, data)
            self._assert_invalid(dst, "ID level mismatch")
        finally:
            td.cleanup()

    def test_requirement_level_exact_type_rejected(self):
        for value in (1.0, True, "1"):
            with self.subTest(value=value):
                td, dst = self._copy_tree()
                try:
                    p, data = self._load(dst, "correctness.yaml")
                    data["requirements"][0]["level"] = value
                    self._write(p, data)
                    self._assert_invalid(dst, "invalid id/level type")
                finally:
                    td.cleanup()

    def test_invalid_sequence_rejected(self):
        for rid in ("COR-1.0", "COR-1.02"):
            with self.subTest(rid=rid):
                td, dst = self._copy_tree()
                try:
                    p, data = self._load(dst, "correctness.yaml")
                    data["requirements"][0]["id"] = rid
                    self._write(p, data)
                    self._assert_invalid(dst, "invalid ID syntax")
                finally:
                    td.cleanup()

    def test_requirement_ordering_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0], data["requirements"][1] = data["requirements"][1], data["requirements"][0]
            self._write(p, data)
            self._assert_invalid(dst, "requirements not sorted")
        finally:
            td.cleanup()

    def test_empty_level_bucket_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"] = [r for r in data["requirements"] if r["level"] != 3]
            self._write(p, data)
            self._assert_invalid(dst, "every level 1..5 must be nonempty")
        finally:
            td.cleanup()

    def test_missing_unconditional_level1_baseline_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            for req in data["requirements"]:
                if req["level"] == 1:
                    req["applicability"] = {"mode": "conditional", "any_of": ["A factual condition exists."]}
            self._write(p, data)
            self._assert_invalid(dst, "no unavoidable Level 1 baseline")
        finally:
            td.cleanup()

    def test_unknown_requirement_field_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["vendor"] = "example"
            self._write(p, data)
            self._assert_invalid(dst, "unknown=['vendor']")
        finally:
            td.cleanup()

    def test_invalid_applicability_mode_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["applicability"] = {"mode": "sometimes"}
            self._write(p, data)
            self._assert_invalid(dst, "invalid applicability mode")
        finally:
            td.cleanup()

    def test_malformed_applicability_mode_type_is_controlled(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["applicability"] = {"mode": ["always"]}
            self._write(p, data)
            self._assert_invalid(dst, "applicability mode must be string")
        finally:
            td.cleanup()

    def test_conditional_applicability_without_predicates_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["applicability"] = {"mode": "conditional"}
            self._write(p, data)
            self._assert_invalid(dst, "conditional applicability requires predicates")
        finally:
            td.cleanup()

    def test_empty_predicate_list_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["applicability"] = {"mode": "conditional", "all_of": []}
            self._write(p, data)
            self._assert_invalid(dst, "all_of must be nonempty list")
        finally:
            td.cleanup()

    def test_malformed_predicate_value_type_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["applicability"] = {"mode": "conditional", "any_of": [7]}
            self._write(p, data)
            self._assert_invalid(dst, "expected nonempty string")
        finally:
            td.cleanup()

    def test_evidence_object_type_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["evidence"] = []
            self._write(p, data)
            self._assert_invalid(dst, "expected mapping")
        finally:
            td.cleanup()

    def test_evidence_required_type_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["evidence"]["required"] = {}
            self._write(p, data)
            self._assert_invalid(dst, "must be nonempty list")
        finally:
            td.cleanup()

    def test_evidence_obligation_object_type_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["evidence"]["required"][0] = "not-a-mapping"
            self._write(p, data)
            self._assert_invalid(dst, "expected mapping")
        finally:
            td.cleanup()

    def test_evidence_classes_container_type_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["evidence"]["required"][0]["classes"] = {"class": "reproducible_test"}
            self._write(p, data)
            self._assert_invalid(dst, "classes: must be nonempty list")
        finally:
            td.cleanup()

    def test_unknown_evidence_class_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["evidence"]["required"][0]["classes"] = ["magic_proof"]
            self._write(p, data)
            self._assert_invalid(dst, "invalid evidence class")
        finally:
            td.cleanup()

    def test_duplicate_evidence_class_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            classes = data["requirements"][0]["evidence"]["required"][0]["classes"]
            data["requirements"][0]["evidence"]["required"][0]["classes"] = [classes[0], classes[0]]
            self._write(p, data)
            self._assert_invalid(dst, "duplicate evidence class")
        finally:
            td.cleanup()

    def test_malformed_evidence_class_type_is_controlled(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["evidence"]["required"][0]["classes"] = [["reproducible_test"]]
            self._write(p, data)
            self._assert_invalid(dst, "evidence class must be string")
        finally:
            td.cleanup()

    def test_malformed_independence_type_is_controlled(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["evidence"]["independence"] = ["none"]
            self._write(p, data)
            self._assert_invalid(dst, "independence must be string")
        finally:
            td.cleanup()

    def test_invalid_independence_value_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][0]["evidence"]["independence"] = "self_review"
            self._write(p, data)
            self._assert_invalid(dst, "independence: invalid value")
        finally:
            td.cleanup()

    def test_missing_level4_independent_review_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            for req in data["requirements"]:
                if req["level"] == 4:
                    req["evidence"]["independence"] = "none"
            self._write(p, data)
            self._assert_invalid(dst, "no Level 4 independent-review requirement")
        finally:
            td.cleanup()

    def test_missing_level5_independent_reproduction_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            for req in data["requirements"]:
                if req["level"] == 5:
                    req["evidence"]["independence"] = "independent_review"
            self._write(p, data)
            self._assert_invalid(dst, "no Level 5 independent-reproduction requirement")
        finally:
            td.cleanup()

    def _requirement(self, filename, rid):
        data = yaml.safe_load((ROOT / "standards" / filename).read_text(encoding="utf-8"))
        return next(req for req in data["requirements"] if req["id"] == rid)

    def test_audit_b_applicability_predicates_use_underlying_facts(self):
        for filename, rid in (("assurance.yaml", "ASR-4.3"), ("security.yaml", "SEC-2.3"),
                              ("security.yaml", "SEC-2.5"), ("privacy.yaml", "PRI-2.5"),
                              ("safety.yaml", "SAF-5.3")):
            with self.subTest(rid=rid):
                app = self._requirement(filename, rid)["applicability"]
                self.assertEqual("conditional", app["mode"])
                predicates = " ".join(app.get("all_of", []) + app.get("any_of", [])).casefold()
                for forbidden in ("documented", "identified", "inventory", "identifies"):
                    self.assertNotIn(forbidden, predicates)

    def test_capability_specific_requirements_are_conditional(self):
        for filename, rid in (("data-integrity.yaml", "DAT-2.2"), ("data-integrity.yaml", "DAT-2.5"),
                              ("observability.yaml", "OBS-3.2"), ("observability.yaml", "OBS-3.3")):
            with self.subTest(rid=rid):
                self.assertEqual("conditional", self._requirement(filename, rid)["applicability"]["mode"])

    def test_retired_compound_ids_are_replaced_with_atomic_controls(self):
        rel = yaml.safe_load((ROOT / "standards" / "reliability.yaml").read_text(encoding="utf-8"))["requirements"]
        rel_by_id = {req["id"]: req for req in rel}
        self.assertNotIn("REL-2.4", rel_by_id)
        self.assertIn("REL-2.5", rel_by_id)
        self.assertIn("REL-2.6", rel_by_id)
        self.assertNotIn("recovery", rel_by_id["REL-2.5"]["statement"].casefold())
        self.assertIn("recovery", rel_by_id["REL-2.6"]["statement"].casefold())

        sup = yaml.safe_load((ROOT / "standards" / "supply-chain.yaml").read_text(encoding="utf-8"))["requirements"]
        sup_by_id = {req["id"]: req for req in sup}
        self.assertNotIn("SUP-4.3", sup_by_id)
        self.assertIn("SUP-4.4", sup_by_id)
        self.assertIn("SUP-4.5", sup_by_id)
        self.assertNotIn("recovery", sup_by_id["SUP-4.4"]["statement"].casefold())
        self.assertIn("recovery", sup_by_id["SUP-4.5"]["statement"].casefold())

    def test_abstraction_boundary_requirements_preserve_properties_without_prescribing_mechanisms(self):
        sec = self._requirement("security.yaml", "SEC-4.1")
        sec_text = " ".join([sec["statement"]] +
                            [ob["demonstrates"] for ob in sec["evidence"]["required"]]).casefold()
        self.assertEqual(4, sec["level"])
        self.assertEqual("always", sec["applicability"]["mode"])
        self.assertEqual("independent_review", sec["evidence"]["independence"])
        self.assertIn("single credible control failure", sec["statement"].casefold())
        self.assertIn("full protected consequence", sec["statement"].casefold())
        self.assertNotIn("defense-in-depth", sec_text)
        self.assertNotIn("independent control boundaries", sec_text)

        saf = self._requirement("safety.yaml", "SAF-4.3")
        saf_text = " ".join([saf["statement"]] +
                            [ob["demonstrates"] for ob in saf["evidence"]["required"]]).casefold()
        self.assertEqual(4, saf["level"])
        self.assertEqual("always", saf["applicability"]["mode"])
        self.assertEqual("independent_review", saf["evidence"]["independence"])
        self.assertIn("single credible control failure", saf["statement"].casefold())
        self.assertIn("severe-harm containment boundary", saf["statement"].casefold())
        self.assertNotIn("defense-in-depth", saf_text)
        self.assertNotIn("defense layers", saf_text)

        mnt = self._requirement("maintainability.yaml", "MNT-3.2")
        mnt_text = " ".join([mnt["statement"]] +
                            [ob["demonstrates"] for ob in mnt["evidence"]["required"]]).casefold()
        self.assertEqual(3, mnt["level"])
        self.assertEqual("always", mnt["applicability"]["mode"])
        self.assertEqual("none", mnt["evidence"]["independence"])
        self.assertIn("material high-change or high-risk areas", mnt["statement"].casefold())
        self.assertIn("representative changes", mnt["statement"].casefold())
        self.assertIn("unrelated system areas", mnt["statement"].casefold())
        self.assertNotIn("architectural boundaries", mnt_text)

        sup = self._requirement("supply-chain.yaml", "SUP-5.3")
        sup_evidence = " ".join(ob["demonstrates"] for ob in sup["evidence"]["required"]).casefold()
        statement = sup["statement"].casefold()
        self.assertEqual(5, sup["level"])
        self.assertEqual("always", sup["applicability"]["mode"])
        self.assertEqual("independent_reproduction", sup["evidence"]["independence"])
        self.assertIn("explicit construction-input boundary", statement)
        self.assertIn("undeclared construction inputs", statement)
        self.assertIn("highest-consequence delivered result", statement)
        self.assertNotIn("independently reproducible", statement)
        self.assertNotIn("hermetic", statement)
        self.assertIn("independent reproduction", sup_evidence)

    def test_eff_4_3_is_retired_without_replacement(self):
        requirements = yaml.safe_load((ROOT / "standards" / "efficiency.yaml").read_text(encoding="utf-8"))["requirements"]
        ids = [req["id"] for req in requirements]
        self.assertEqual([
            "EFF-1.1", "EFF-2.2", "EFF-2.3", "EFF-3.2", "EFF-3.3",
            "EFF-4.2", "EFF-5.2", "EFF-5.3",
        ], ids)
        eff_4_2 = next(req for req in requirements if req["id"] == "EFF-4.2")
        self.assertEqual(4, eff_4_2["level"])
        self.assertEqual("independent_review", eff_4_2["evidence"]["independence"])

    def test_invalid_utf8_standards_file_is_controlled(self):
        td, dst = self._copy_tree()
        try:
            p = dst / "standards" / "correctness.yaml"
            p.write_bytes(b"\xff\xfedimension: COR\n")
            self._assert_invalid(dst, "invalid UTF-8")
        finally:
            td.cleanup()

    def test_mixed_type_unknown_mapping_keys_are_controlled_and_deterministic(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data[7] = "integer-key"
            data["vendor"] = "string-key"
            self._write(p, data)
            self._assert_invalid(dst, "unknown=[7, 'vendor']")
        finally:
            td.cleanup()

    def test_duplicate_normalized_statement_rejected(self):
        td, dst = self._copy_tree()
        try:
            p, data = self._load(dst, "correctness.yaml")
            data["requirements"][1]["statement"] = "  " + data["requirements"][0]["statement"].upper() + "  "
            self._write(p, data)
            self._assert_invalid(dst, "exact duplicate normalized requirement statements")
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
