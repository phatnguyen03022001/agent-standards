#!/usr/bin/env python3
"""Deterministically validate the canonical standards definition; never assess targets."""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

ROOT = Path(__file__).resolve().parents[1]
STANDARDS = ROOT / "standards"
MANIFEST = STANDARDS / "manifest.yaml"
ALLOWED_EVIDENCE = {
    "artifact_inspection", "analysis", "reproducible_test", "runtime_observation",
    "operational_exercise", "provenance_attestation", "formal_verification",
}
ALLOWED_INDEPENDENCE = {"none", "independent_review", "independent_reproduction"}
REQ_FIELDS = {"id", "level", "statement", "intent", "applicability", "evidence"}
APP_FIELDS = {"mode", "all_of", "any_of"}
EVIDENCE_FIELDS = {"required", "independence"}
OBLIGATION_FIELDS = {"demonstrates", "classes"}
ID_RE = re.compile(r"^([A-Z]{3})-([1-5])\.([1-9][0-9]*)$")


class ValidationError(Exception):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=False)
        try:
            hash(key)
        except TypeError as exc:
            raise ValidationError(f"YAML mapping key must be hashable scalar: {key!r}") from exc
        if key in seen:
            raise ValidationError(f"duplicate YAML mapping key: {key!r}")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _reject_obscuring_yaml(text: str, path: Path) -> None:
    try:
        for event in yaml.parse(text):
            if isinstance(event, AliasEvent) or getattr(event, "anchor", None) is not None:
                raise ValidationError(f"{path}: YAML anchors/aliases are forbidden")
        root = yaml.compose(text)
    except yaml.YAMLError as exc:
        raise ValidationError(f"{path}: malformed YAML: {exc}") from exc

    def walk(node):
        if node is None:
            return
        if isinstance(node, ScalarNode):
            if node.tag not in {
                "tag:yaml.org,2002:str", "tag:yaml.org,2002:int", "tag:yaml.org,2002:bool",
                "tag:yaml.org,2002:null", "tag:yaml.org,2002:float",
            }:
                raise ValidationError(f"{path}: custom YAML tag forbidden: {node.tag}")
        elif isinstance(node, MappingNode):
            if node.tag != "tag:yaml.org,2002:map":
                raise ValidationError(f"{path}: custom YAML mapping tag forbidden: {node.tag}")
            for k, v in node.value:
                walk(k); walk(v)
        elif isinstance(node, SequenceNode):
            if node.tag != "tag:yaml.org,2002:seq":
                raise ValidationError(f"{path}: custom YAML sequence tag forbidden: {node.tag}")
            for item in node.value:
                walk(item)
    walk(root)


def load_yaml(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{path}: invalid UTF-8: {exc}") from exc
    _reject_obscuring_yaml(text, path)
    try:
        return yaml.load(text, Loader=StrictLoader)
    except (yaml.YAMLError, ValidationError) as exc:
        raise ValidationError(f"{path}: {exc}") from exc


def _stable_sorted(values):
    return sorted(values, key=lambda value: (type(value).__module__, type(value).__qualname__, repr(value)))


def exact_keys(obj, expected, where):
    if type(obj) is not dict:
        raise ValidationError(f"{where}: expected mapping")
    keys = set(obj)
    missing, unknown = expected - keys, keys - expected
    if missing or unknown:
        raise ValidationError(f"{where}: missing={_stable_sorted(missing)} unknown={_stable_sorted(unknown)}")


def nonempty_string(value, where):
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{where}: expected nonempty string")


def validate_app(app, where):
    if type(app) is not dict:
        raise ValidationError(f"{where}: applicability must be mapping")
    unknown = set(app) - APP_FIELDS
    if unknown:
        raise ValidationError(f"{where}: unknown applicability fields {_stable_sorted(unknown)}")
    mode = app.get("mode")
    if type(mode) is not str:
        raise ValidationError(f"{where}: applicability mode must be string")
    if mode not in {"always", "conditional"}:
        raise ValidationError(f"{where}: invalid applicability mode")
    predicates = []
    for key in ("all_of", "any_of"):
        if key in app:
            if mode == "always":
                raise ValidationError(f"{where}: {key} forbidden for always applicability")
            vals = app[key]
            if type(vals) is not list or not vals:
                raise ValidationError(f"{where}: {key} must be nonempty list")
            for i, val in enumerate(vals):
                nonempty_string(val, f"{where}.{key}[{i}]")
            predicates.extend(vals)
    if mode == "conditional" and not predicates:
        raise ValidationError(f"{where}: conditional applicability requires predicates")


def validate_evidence(ev, where):
    exact_keys(ev, EVIDENCE_FIELDS, where)
    required = ev["required"]
    if type(required) is not list or not required:
        raise ValidationError(f"{where}.required: must be nonempty list")
    for i, ob in enumerate(required):
        ow = f"{where}.required[{i}]"
        exact_keys(ob, OBLIGATION_FIELDS, ow)
        nonempty_string(ob["demonstrates"], f"{ow}.demonstrates")
        classes = ob["classes"]
        if type(classes) is not list or not classes:
            raise ValidationError(f"{ow}.classes: must be nonempty list")
        for j, evidence_class in enumerate(classes):
            if type(evidence_class) is not str:
                raise ValidationError(f"{ow}.classes[{j}]: evidence class must be string")
            if evidence_class not in ALLOWED_EVIDENCE:
                raise ValidationError(f"{ow}.classes: invalid evidence class")
        if len(classes) != len(set(classes)):
            raise ValidationError(f"{ow}.classes: duplicate evidence class")
    independence = ev["independence"]
    if type(independence) is not str:
        raise ValidationError(f"{where}.independence: independence must be string")
    if independence not in ALLOWED_INDEPENDENCE:
        raise ValidationError(f"{where}.independence: invalid value")


def normalized_statement(s):
    return " ".join(s.split()).casefold()


def validate(root=ROOT):
    standards = root / "standards"
    manifest = load_yaml(standards / "manifest.yaml")
    exact_keys(manifest, {"generation", "dimensions"}, "manifest")
    generation = manifest["generation"]
    if type(generation) is not int or generation != 1:
        raise ValidationError("manifest.generation must be exactly integer 1")
    dims = manifest["dimensions"]
    if type(dims) is not list or len(dims) != 14:
        raise ValidationError("manifest must declare exactly 14 dimensions")
    expected_codes = ["COR","SEC","PRI","DAT","REL","PER","OBS","MNT","OPS","CMP","SUP","EFF","ASR","SAF"]
    codes, keys, files = [], [], []
    for i, d in enumerate(dims):
        exact_keys(d, {"code", "key", "name", "file"}, f"manifest.dimensions[{i}]")
        for field in ("code", "key", "name", "file"):
            nonempty_string(d[field], f"manifest.dimensions[{i}].{field}")
        codes.append(d["code"]); keys.append(d["key"]); files.append(d["file"])
    for label, vals in (("code", codes), ("key", keys), ("filename", files)):
        if len(vals) != len(set(vals)):
            raise ValidationError(f"duplicate dimension {label}")
    if codes != expected_codes:
        raise ValidationError("dimension registry code/order mismatch")
    declared = set(files)
    actual = {p.name for p in standards.glob("*.yaml") if p.name != "manifest.yaml"}
    if actual != declared:
        raise ValidationError(f"standard file registry mismatch missing={sorted(declared-actual)} undeclared={sorted(actual-declared)}")

    all_ids, statements = [], []
    for d in dims:
        path = standards / d["file"]
        if not path.is_file():
            raise ValidationError(f"manifest entry without file: {d['file']}")
        doc = load_yaml(path)
        exact_keys(doc, {"dimension", "applicability", "requirements"}, path.name)
        nonempty_string(doc["dimension"], f"{path.name}.dimension")
        if doc["dimension"] != d["code"]:
            raise ValidationError(f"{path.name}: dimension code outside/mismatches registry")
        validate_app(doc["applicability"], f"{path.name}.applicability")
        reqs = doc["requirements"]
        if type(reqs) is not list or not reqs:
            raise ValidationError(f"{path.name}: requirements must be nonempty list")
        level_counts = Counter()
        has_l1_always = False
        has_l4_review = False
        has_l5_repro = False
        previous = None
        for i, req in enumerate(reqs):
            where = f"{path.name}.requirements[{i}]"
            exact_keys(req, REQ_FIELDS, where)
            rid, level = req["id"], req["level"]
            if type(rid) is not str or type(level) is not int:
                raise ValidationError(f"{where}: invalid id/level type")
            m = ID_RE.fullmatch(rid)
            if not m:
                raise ValidationError(f"{where}: invalid ID syntax")
            code, id_level, seq = m.group(1), int(m.group(2)), int(m.group(3))
            if code != d["code"]:
                raise ValidationError(f"{where}: ID dimension prefix mismatch")
            if id_level != level or level not in range(1, 6):
                raise ValidationError(f"{where}: ID level mismatch or level outside 1..5")
            order = (level, seq)
            if previous is not None and order <= previous:
                raise ValidationError(f"{where}: requirements not sorted by numeric level then sequence")
            previous = order
            nonempty_string(req["statement"], f"{where}.statement")
            nonempty_string(req["intent"], f"{where}.intent")
            validate_app(req["applicability"], f"{where}.applicability")
            validate_evidence(req["evidence"], f"{where}.evidence")
            level_counts[level] += 1
            has_l1_always |= level == 1 and req["applicability"].get("mode") == "always"
            has_l4_review |= level == 4 and req["evidence"]["independence"] == "independent_review"
            has_l5_repro |= level == 5 and req["evidence"]["independence"] == "independent_reproduction"
            all_ids.append(rid); statements.append(normalized_statement(req["statement"]))
        if set(level_counts) != {1,2,3,4,5}:
            raise ValidationError(f"{path.name}: every level 1..5 must be nonempty")
        if not has_l1_always:
            raise ValidationError(f"{path.name}: no unavoidable Level 1 baseline")
        if not has_l4_review:
            raise ValidationError(f"{path.name}: no Level 4 independent-review requirement")
        if not has_l5_repro:
            raise ValidationError(f"{path.name}: no Level 5 independent-reproduction requirement")
    if len(all_ids) != len(set(all_ids)):
        raise ValidationError("duplicate requirement IDs globally")
    duplicates = [s for s, n in Counter(statements).items() if n > 1]
    if duplicates:
        raise ValidationError(f"exact duplicate normalized requirement statements: {duplicates}")
    return True


def main():
    try:
        validate()
    except (ValidationError, OSError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print("VALID: standards definition")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
