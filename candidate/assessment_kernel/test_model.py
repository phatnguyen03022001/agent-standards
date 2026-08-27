import inspect
import pathlib
import unittest

from model import (
    Applicability, Assessment, ChangeBasis, Dependency, Disposition, EvidenceRef,
    HistoryRelation, Judgment, NormativeAuthority, SubjectIdentity,
    TrajectoryDirection, TrajectoryFacts, evaluate, establish_trajectory,
)

AUTH = NormativeAuthority("standard://example/control", "sha256:abc")
SUBJECT = SubjectIdentity(
    "service", "svc-1",
    (("source_revision", "same-source"), ("environment", "prod"), ("population", "cohort-a")),
    ("environment", "population"),
)


def evidence(ref, *inferences):
    return EvidenceRef(ref, frozenset(inferences))


def assessment(**overrides):
    values = dict(
        assessment_id="a-1", claim_id="claim.outcome", family="Product",
        applicability=Applicability.APPLICABLE, judgment=Judgment.PASS, disposition=None,
        authority=AUTH, subject=SUBJECT,
        evidence=(evidence("ev-1", "observed_outcome"),),
        asserted_inference="observed_outcome", dependencies=(),
    )
    values.update(overrides)
    return Assessment(**values)


def trajectory_facts(*, comparable=True, changed=True, bases=None):
    return TrajectoryFacts(
        comparable=comparable,
        exact_property_changed=changed,
        direction=TrajectoryDirection.IMPROVEMENT,
        change_bases=frozenset({ChangeBasis.PROCESS} if bases is None else bases),
        history_relation=HistoryRelation.NEW_ASSESSMENT,
    )


class AssessmentKernelCandidateTests(unittest.TestCase):
    def test_inference_inflation_is_rejected(self):
        result = evaluate(assessment(asserted_inference="product_caused_outcome"))
        self.assertFalse(result.accepted)
        self.assertFalse(result.obligation_satisfied)
        self.assertIn("unsupported_inference", result.reasons)

    def test_unknown_applicability_cannot_become_not_applicable(self):
        unknown = evaluate(assessment(applicability=Applicability.UNKNOWN, judgment=None))
        na = evaluate(assessment(applicability=Applicability.NOT_APPLICABLE, judgment=None))
        self.assertEqual(Applicability.UNKNOWN, unknown.applicability)
        self.assertEqual(Applicability.NOT_APPLICABLE, na.applicability)
        self.assertFalse(unknown.obligation_satisfied)
        self.assertFalse(na.obligation_satisfied)

    def test_only_pass_satisfies_applicable_obligation_and_exception_never_launders(self):
        for judgment in (Judgment.PARTIAL, Judgment.GAP, Judgment.UNKNOWN):
            self.assertFalse(evaluate(assessment(judgment=judgment)).obligation_satisfied)
        self.assertTrue(evaluate(assessment(judgment=Judgment.PASS)).obligation_satisfied)
        gap = evaluate(assessment(judgment=Judgment.GAP, disposition=Disposition.EXCEPTION))
        self.assertTrue(gap.accepted)
        self.assertFalse(gap.obligation_satisfied)
        self.assertFalse(evaluate(assessment(disposition=Disposition.EXCEPTION)).accepted)

    def test_exact_authority_evidence_and_claim_relative_context_are_required(self):
        self.assertIn("missing_normative_identity", evaluate(assessment(authority=NormativeAuthority("", ""))).reasons)
        self.assertIn("missing_evidence", evaluate(assessment(evidence=())).reasons)
        incomplete = SubjectIdentity("service", "svc-1", (("environment", "prod"),), ("environment", "population"))
        self.assertIn("missing_material_context", evaluate(assessment(subject=incomplete)).reasons)
        narrow = SubjectIdentity("migration_run", "run-7", (("dataset", "d1"),), ("dataset",))
        self.assertTrue(evaluate(assessment(subject=narrow)).accepted)

    def test_same_source_revision_can_have_substantive_positive_trajectory(self):
        before = assessment(assessment_id="before", judgment=Judgment.PARTIAL)
        after = assessment(assessment_id="after", judgment=Judgment.PASS)
        facts = trajectory_facts(bases={ChangeBasis.SUBJECT, ChangeBasis.OBSERVATION})
        self.assertTrue(establish_trajectory(before, after, facts).established)

    def test_knowledge_gain_does_not_prove_subject_improvement(self):
        before = assessment(assessment_id="before", judgment=Judgment.UNKNOWN)
        after = assessment(assessment_id="after", judgment=Judgment.PASS)
        self.assertFalse(establish_trajectory(before, after, trajectory_facts(changed=False)).established)

    def test_assessment_correction_or_supersession_does_not_prove_subject_improvement(self):
        facts = TrajectoryFacts(True, False, TrajectoryDirection.IMPROVEMENT,
                                frozenset({ChangeBasis.ASSESSMENT_CORRECTION}), HistoryRelation.SUPERSEDES)
        result = establish_trajectory(
            assessment(assessment_id="before", judgment=Judgment.GAP),
            assessment(assessment_id="after", judgment=Judgment.PASS), facts,
        )
        self.assertFalse(result.established)
        self.assertEqual(HistoryRelation.SUPERSEDES, result.history_relation)

    def test_insufficient_comparability_blocks_trajectory_even_when_status_changes(self):
        changed_subject = SubjectIdentity(
            "service", "svc-1",
            (("source_revision", "same-source"), ("environment", "prod"), ("population", "cohort-b")),
            ("environment", "population"),
        )
        self.assertFalse(establish_trajectory(
            assessment(assessment_id="before", judgment=Judgment.GAP),
            assessment(assessment_id="after", subject=changed_subject),
            trajectory_facts(comparable=False, bases={ChangeBasis.SUBJECT}),
        ).established)

    def test_cross_family_non_substitution_and_explicit_dependency(self):
        transparency = assessment(claim_id="product.transparency", asserted_inference="clear",
                                  evidence=(evidence("p", "clear"),))
        security_gap = assessment(assessment_id="sec", claim_id="engineering.security", family="Engineering",
                                  judgment=Judgment.GAP, asserted_inference="checked",
                                  evidence=(evidence("s", "checked"),))
        self.assertTrue(evaluate(transparency).obligation_satisfied)
        self.assertFalse(evaluate(security_gap).obligation_satisfied)
        result = evaluate(assessment(dependencies=(Dependency("engineering.security", False),)))
        self.assertFalse(result.accepted)
        self.assertIn("unmet_dependency", result.reasons)

    def test_process_market_basis_can_establish_exact_property_trajectory(self):
        bases = {ChangeBasis.PROCESS, ChangeBasis.MARKET}
        result = establish_trajectory(
            assessment(assessment_id="before", judgment=Judgment.PARTIAL),
            assessment(assessment_id="after"), trajectory_facts(bases=bases),
        )
        self.assertTrue(result.established)
        self.assertEqual(frozenset(bases), result.change_bases)

    def test_multi_causal_change_basis_is_preserved(self):
        bases = {ChangeBasis.SUBJECT, ChangeBasis.OBSERVATION, ChangeBasis.PROCESS}
        result = establish_trajectory(
            assessment(assessment_id="before", judgment=Judgment.PARTIAL),
            assessment(assessment_id="after"), trajectory_facts(bases=bases),
        )
        self.assertTrue(result.established)
        self.assertEqual(frozenset(bases), result.change_bases)

    def test_anonymous_evidence_identity_is_rejected(self):
        for identifier in ("", "   "):
            result = evaluate(assessment(evidence=(evidence(identifier, "observed_outcome"),)))
            self.assertFalse(result.accepted)
            self.assertFalse(result.obligation_satisfied)

    def test_blank_semantic_identity_tokens_are_rejected(self):
        cases = (
            {"assessment_id": "   "}, {"claim_id": "   "}, {"family": "   "},
            {"authority": NormativeAuthority("   ", "sha256:abc")},
            {"authority": NormativeAuthority("standard://example/control", "   ")},
            {"subject": SubjectIdentity("   ", "svc-1", SUBJECT.material_context, SUBJECT.required_context)},
            {"subject": SubjectIdentity("service", "   ", SUBJECT.material_context, SUBJECT.required_context)},
            {"asserted_inference": "   ", "evidence": (evidence("ev-1", "   "),)},
            {"dependencies": (Dependency("   ", True),)},
        )
        for overrides in cases:
            result = evaluate(assessment(**overrides))
            self.assertFalse(result.accepted)
            self.assertFalse(result.obligation_satisfied)

    def test_material_context_identity_rejects_blank_and_duplicate_tokens(self):
        subjects = (
            SubjectIdentity("service", "svc-1", (("environment", "prod"), (" ", "x")), ("environment",)),
            SubjectIdentity("service", "svc-1", (("environment", "prod"), ("population", " ")), ("environment",)),
            SubjectIdentity("service", "svc-1", (("environment", "prod"), ("environment", "staging")), ("environment",)),
            SubjectIdentity("service", "svc-1", (("environment", "prod"),), ("environment", "environment")),
            SubjectIdentity("service", "svc-1", (("environment", "prod"),), ("environment", "   ")),
        )
        for subject in subjects:
            self.assertFalse(evaluate(assessment(subject=subject)).accepted)

    def test_trajectory_endpoints_require_valid_attributable_identity(self):
        invalid = (
            assessment(assessment_id="   "), assessment(claim_id="   "), assessment(family="   "),
            assessment(authority=NormativeAuthority("standard://example/control", "   ")),
            assessment(subject=SubjectIdentity("service", "svc-1",
                                               (("environment", "prod"), ("environment", "staging")),
                                               ("environment",))),
        )
        valid = assessment(assessment_id="valid")
        facts = trajectory_facts()
        for endpoint in invalid:
            self.assertFalse(establish_trajectory(endpoint, valid, facts).established)
            self.assertFalse(establish_trajectory(valid, endpoint, facts).established)

    def test_trusted_dependency_and_trajectory_facts_remain_separate_boundaries(self):
        self.assertTrue(evaluate(assessment(dependencies=(Dependency("engineering.security", True),))).obligation_satisfied)
        before = assessment(assessment_id="before", judgment=None, evidence=(), asserted_inference="")
        after = assessment(assessment_id="after", judgment=None, evidence=(), asserted_inference="")
        self.assertFalse(evaluate(before).accepted)
        self.assertFalse(evaluate(after).accepted)
        self.assertTrue(establish_trajectory(before, after, trajectory_facts()).established)

    def test_no_synthetic_aggregation_or_archetype_control_surface_exists(self):
        import model
        forbidden = {"aggregate", "score", "overall_score", "family_score", "dimension_score", "maturity_score", "percentage"}
        self.assertTrue(forbidden.isdisjoint(set(dir(model))))
        source = pathlib.Path(inspect.getsourcefile(model)).read_text(encoding="utf-8").lower()
        for token in ("archetype_a", "archetype_b", "archetype_c", "archetype_d"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
