import inspect
import pathlib
import unittest

from model import (
    Applicability,
    Assessment,
    ChangeBasis,
    Dependency,
    Disposition,
    EvidenceRef,
    HistoryRelation,
    Judgment,
    NormativeAuthority,
    SubjectIdentity,
    TrajectoryDirection,
    TrajectoryFacts,
    evaluate,
    establish_trajectory,
)


AUTH = NormativeAuthority("standard://example/control", "sha256:abc")
SUBJECT = SubjectIdentity(
    kind="service",
    identifier="svc-1",
    material_context=(
        ("source_revision", "same-source"),
        ("environment", "prod"),
        ("population", "cohort-a"),
    ),
    required_context=("environment", "population"),
)


def evidence(ref, *inferences):
    return EvidenceRef(ref, frozenset(inferences))


def assessment(**overrides):
    values = dict(
        assessment_id="a-1",
        claim_id="claim.outcome",
        family="Product",
        applicability=Applicability.APPLICABLE,
        judgment=Judgment.PASS,
        disposition=None,
        authority=AUTH,
        subject=SUBJECT,
        evidence=(evidence("ev-1", "observed_outcome"),),
        asserted_inference="observed_outcome",
        dependencies=(),
    )
    values.update(overrides)
    return Assessment(**values)


class AssessmentKernelCandidateTests(unittest.TestCase):
    def test_inference_inflation_is_rejected(self):
        result = evaluate(assessment(asserted_inference="product_caused_outcome"))
        self.assertFalse(result.accepted)
        self.assertFalse(result.obligation_satisfied)
        self.assertIn("unsupported_inference", result.reasons)

    def test_unknown_applicability_cannot_become_not_applicable(self):
        unknown = evaluate(assessment(applicability=Applicability.UNKNOWN, judgment=None))
        not_applicable = evaluate(
            assessment(applicability=Applicability.NOT_APPLICABLE, judgment=None)
        )
        self.assertEqual(Applicability.UNKNOWN, unknown.applicability)
        self.assertEqual(Applicability.NOT_APPLICABLE, not_applicable.applicability)
        self.assertFalse(unknown.obligation_satisfied)
        self.assertFalse(not_applicable.obligation_satisfied)

    def test_only_pass_satisfies_applicable_obligation_and_exception_never_launders(self):
        for judgment in (Judgment.PARTIAL, Judgment.GAP, Judgment.UNKNOWN):
            with self.subTest(judgment=judgment):
                self.assertFalse(evaluate(assessment(judgment=judgment)).obligation_satisfied)
        self.assertTrue(evaluate(assessment(judgment=Judgment.PASS)).obligation_satisfied)
        excepted_gap = evaluate(
            assessment(judgment=Judgment.GAP, disposition=Disposition.EXCEPTION)
        )
        self.assertTrue(excepted_gap.accepted)
        self.assertFalse(excepted_gap.obligation_satisfied)
        pass_exception = evaluate(
            assessment(judgment=Judgment.PASS, disposition=Disposition.EXCEPTION)
        )
        self.assertFalse(pass_exception.accepted)

    def test_exact_authority_evidence_and_claim_relative_context_are_required(self):
        missing_authority = evaluate(
            assessment(authority=NormativeAuthority("", ""))
        )
        self.assertFalse(missing_authority.accepted)
        self.assertIn("missing_normative_identity", missing_authority.reasons)

        missing_evidence = evaluate(assessment(evidence=()))
        self.assertFalse(missing_evidence.accepted)
        self.assertIn("missing_evidence", missing_evidence.reasons)

        incomplete_subject = SubjectIdentity(
            kind="service",
            identifier="svc-1",
            material_context=(("environment", "prod"),),
            required_context=("environment", "population"),
        )
        missing_context = evaluate(assessment(subject=incomplete_subject))
        self.assertFalse(missing_context.accepted)
        self.assertIn("missing_material_context", missing_context.reasons)

        narrow_subject = SubjectIdentity(
            kind="migration_run",
            identifier="run-7",
            material_context=(("dataset", "d1"),),
            required_context=("dataset",),
        )
        self.assertTrue(evaluate(assessment(subject=narrow_subject)).accepted)

    def test_same_source_revision_can_have_substantive_positive_trajectory(self):
        before = assessment(
            assessment_id="before",
            judgment=Judgment.PARTIAL,
            evidence=(evidence("ev-before", "observed_outcome"),),
        )
        after = assessment(
            assessment_id="after",
            judgment=Judgment.PASS,
            evidence=(evidence("ev-after", "observed_outcome"),),
        )
        facts = TrajectoryFacts(
            comparable=True,
            exact_property_changed=True,
            direction=TrajectoryDirection.IMPROVEMENT,
            change_bases=frozenset({ChangeBasis.SUBJECT, ChangeBasis.OBSERVATION}),
            history_relation=HistoryRelation.NEW_ASSESSMENT,
        )
        result = establish_trajectory(before, after, facts)
        self.assertEqual(TrajectoryDirection.IMPROVEMENT, result.direction)
        self.assertTrue(result.established)

    def test_knowledge_gain_does_not_prove_subject_improvement(self):
        before = assessment(assessment_id="before", judgment=Judgment.UNKNOWN)
        after = assessment(assessment_id="after", judgment=Judgment.PASS)
        facts = TrajectoryFacts(
            comparable=True,
            exact_property_changed=False,
            direction=TrajectoryDirection.IMPROVEMENT,
            change_bases=frozenset({ChangeBasis.OBSERVATION}),
            history_relation=HistoryRelation.NEW_ASSESSMENT,
        )
        self.assertFalse(establish_trajectory(before, after, facts).established)

    def test_assessment_correction_or_supersession_does_not_prove_subject_improvement(self):
        before = assessment(assessment_id="before", judgment=Judgment.GAP)
        after = assessment(assessment_id="after", judgment=Judgment.PASS)
        facts = TrajectoryFacts(
            comparable=True,
            exact_property_changed=False,
            direction=TrajectoryDirection.IMPROVEMENT,
            change_bases=frozenset({ChangeBasis.ASSESSMENT_CORRECTION}),
            history_relation=HistoryRelation.SUPERSEDES,
        )
        result = establish_trajectory(before, after, facts)
        self.assertFalse(result.established)
        self.assertEqual(HistoryRelation.SUPERSEDES, result.history_relation)

    def test_insufficient_comparability_blocks_trajectory_even_when_status_changes(self):
        before = assessment(assessment_id="before", judgment=Judgment.GAP)
        changed_subject = SubjectIdentity(
            kind="service",
            identifier="svc-1",
            material_context=(
                ("source_revision", "same-source"),
                ("environment", "prod"),
                ("population", "cohort-b"),
            ),
            required_context=("environment", "population"),
        )
        after = assessment(
            assessment_id="after", judgment=Judgment.PASS, subject=changed_subject
        )
        facts = TrajectoryFacts(
            comparable=False,
            exact_property_changed=True,
            direction=TrajectoryDirection.IMPROVEMENT,
            change_bases=frozenset({ChangeBasis.SUBJECT}),
            history_relation=HistoryRelation.NEW_ASSESSMENT,
        )
        self.assertFalse(establish_trajectory(before, after, facts).established)

    def test_cross_family_non_substitution_and_explicit_dependency(self):
        transparency = assessment(
            claim_id="product.transparency",
            family="Product",
            asserted_inference="expectations_are_clear",
            evidence=(evidence("product-ev", "expectations_are_clear"),),
        )
        security_gap = assessment(
            assessment_id="sec",
            claim_id="engineering.security",
            family="Engineering",
            judgment=Judgment.GAP,
            asserted_inference="security_control_evaluated",
            evidence=(evidence("sec-ev", "security_control_evaluated"),),
        )
        self.assertTrue(evaluate(transparency).obligation_satisfied)
        self.assertFalse(evaluate(security_gap).obligation_satisfied)

        dependent = assessment(
            claim_id="product.safe_expectation",
            family="Product",
            asserted_inference="safe_expectation_supported",
            evidence=(evidence("dep-ev", "safe_expectation_supported"),),
            dependencies=(
                Dependency("engineering.security", satisfied=False),
            ),
        )
        result = evaluate(dependent)
        self.assertFalse(result.accepted)
        self.assertFalse(result.obligation_satisfied)
        self.assertIn("unmet_dependency", result.reasons)

    def test_process_market_basis_can_establish_exact_property_trajectory(self):
        before = assessment(assessment_id="before", judgment=Judgment.PARTIAL)
        after = assessment(assessment_id="after", judgment=Judgment.PASS)
        bases = frozenset({ChangeBasis.PROCESS, ChangeBasis.MARKET})
        facts = TrajectoryFacts(
            comparable=True,
            exact_property_changed=True,
            direction=TrajectoryDirection.IMPROVEMENT,
            change_bases=bases,
            history_relation=HistoryRelation.NEW_ASSESSMENT,
        )
        result = establish_trajectory(before, after, facts)
        self.assertTrue(result.established)
        self.assertEqual(bases, result.change_bases)

    def test_multi_causal_change_basis_is_preserved(self):
        before = assessment(assessment_id="before", judgment=Judgment.PARTIAL)
        after = assessment(assessment_id="after", judgment=Judgment.PASS)
        bases = frozenset(
            {ChangeBasis.SUBJECT, ChangeBasis.OBSERVATION, ChangeBasis.PROCESS}
        )
        facts = TrajectoryFacts(
            comparable=True,
            exact_property_changed=True,
            direction=TrajectoryDirection.IMPROVEMENT,
            change_bases=bases,
            history_relation=HistoryRelation.NEW_ASSESSMENT,
        )
        result = establish_trajectory(before, after, facts)
        self.assertTrue(result.established)
        self.assertEqual(bases, result.change_bases)

    def test_no_synthetic_aggregation_or_archetype_control_surface_exists(self):
        import model

        public_names = set(dir(model))
        forbidden_api = {
            "aggregate",
            "score",
            "overall_score",
            "family_score",
            "dimension_score",
            "maturity_score",
            "percentage",
        }
        self.assertTrue(forbidden_api.isdisjoint(public_names))

        source = pathlib.Path(inspect.getsourcefile(model)).read_text(encoding="utf-8")
        for token in ("archetype_a", "archetype_b", "archetype_c", "archetype_d"):
            self.assertNotIn(token, source.lower())


if __name__ == "__main__":
    unittest.main()
