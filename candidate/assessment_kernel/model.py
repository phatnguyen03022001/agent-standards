from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional, Tuple


CANDIDATE_STATUS = "NON_RELEASED_CANDIDATE"
CANDIDATE_AUTHORITY = "NONE"
CANDIDATE_GENERATION = "NOT_ASSIGNED"


def _identifying(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip())


class Applicability(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class Judgment(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    GAP = "GAP"
    UNKNOWN = "UNKNOWN"


class Disposition(str, Enum):
    EXCEPTION = "EXCEPTION"


class ChangeBasis(str, Enum):
    SUBJECT = "SUBJECT"
    OBSERVATION = "OBSERVATION"
    ASSESSMENT_CORRECTION = "ASSESSMENT_CORRECTION"
    STANDARDS = "STANDARDS"
    SCOPE = "SCOPE"
    PROCESS = "PROCESS"
    MARKET = "MARKET"
    OTHER = "OTHER"


class HistoryRelation(str, Enum):
    NEW_ASSESSMENT = "NEW_ASSESSMENT"
    CORRECTS = "CORRECTS"
    SUPERSEDES = "SUPERSEDES"


class TrajectoryDirection(str, Enum):
    IMPROVEMENT = "IMPROVEMENT"
    REGRESSION = "REGRESSION"


@dataclass(frozen=True)
class NormativeAuthority:
    identifier: str
    immutable_revision: str


@dataclass(frozen=True)
class SubjectIdentity:
    kind: str
    identifier: str
    material_context: Tuple[Tuple[str, str], ...] = ()
    required_context: Tuple[str, ...] = ()

    def has_required_context(self) -> bool:
        if not _identifying(self.kind) or not _identifying(self.identifier):
            return False

        context_keys = []
        for key, value in self.material_context:
            if not _identifying(key) or not _identifying(value):
                return False
            context_keys.append(key)
        if len(context_keys) != len(set(context_keys)):
            return False

        if any(not _identifying(key) for key in self.required_context):
            return False
        if len(self.required_context) != len(set(self.required_context)):
            return False

        return set(self.required_context) <= set(context_keys)


@dataclass(frozen=True)
class EvidenceRef:
    identifier: str
    supported_inferences: FrozenSet[str]


@dataclass(frozen=True)
class Dependency:
    claim_id: str
    satisfied: bool


@dataclass(frozen=True)
class Assessment:
    assessment_id: str
    claim_id: str
    family: str
    applicability: Applicability
    judgment: Optional[Judgment]
    disposition: Optional[Disposition]
    authority: NormativeAuthority
    subject: SubjectIdentity
    evidence: Tuple[EvidenceRef, ...]
    asserted_inference: str
    dependencies: Tuple[Dependency, ...] = ()


@dataclass(frozen=True)
class Evaluation:
    applicability: Applicability
    judgment: Optional[Judgment]
    disposition: Optional[Disposition]
    accepted: bool
    obligation_satisfied: bool
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class TrajectoryFacts:
    comparable: bool
    exact_property_changed: bool
    direction: TrajectoryDirection
    change_bases: FrozenSet[ChangeBasis]
    history_relation: HistoryRelation


@dataclass(frozen=True)
class TrajectoryResult:
    established: bool
    direction: Optional[TrajectoryDirection]
    change_bases: FrozenSet[ChangeBasis]
    history_relation: HistoryRelation
    reasons: Tuple[str, ...]


def evaluate(assessment: Assessment) -> Evaluation:
    reasons = []

    if not _identifying(assessment.assessment_id):
        reasons.append("missing_assessment_identity")
    if not _identifying(assessment.claim_id):
        reasons.append("missing_claim_identity")
    if not _identifying(assessment.family):
        reasons.append("missing_family_identity")
    if not _identifying(assessment.authority.identifier) or not _identifying(assessment.authority.immutable_revision):
        reasons.append("missing_normative_identity")
    if not assessment.subject.has_required_context():
        reasons.append("missing_material_context")
    if not assessment.evidence:
        reasons.append("missing_evidence")
    elif any(not _identifying(item.identifier) for item in assessment.evidence):
        reasons.append("missing_evidence_identity")
    if not _identifying(assessment.asserted_inference):
        reasons.append("missing_asserted_inference")
    elif assessment.evidence and not any(
        _identifying(item.identifier)
        and assessment.asserted_inference in item.supported_inferences
        for item in assessment.evidence
    ):
        reasons.append("unsupported_inference")

    if assessment.applicability is Applicability.APPLICABLE:
        if assessment.judgment is None:
            reasons.append("missing_applicable_judgment")
        if assessment.disposition is Disposition.EXCEPTION and assessment.judgment is Judgment.PASS:
            reasons.append("exception_cannot_wrap_pass")
        if any(not _identifying(dependency.claim_id) for dependency in assessment.dependencies):
            reasons.append("missing_dependency_identity")
        if any(not dependency.satisfied for dependency in assessment.dependencies):
            reasons.append("unmet_dependency")
    else:
        if assessment.judgment is not None:
            reasons.append("judgment_requires_applicable_claim")
        if assessment.disposition is not None:
            reasons.append("disposition_requires_applicable_claim")

    accepted = not reasons
    obligation_satisfied = (
        accepted
        and assessment.applicability is Applicability.APPLICABLE
        and assessment.judgment is Judgment.PASS
        and assessment.disposition is None
    )
    return Evaluation(
        applicability=assessment.applicability,
        judgment=assessment.judgment,
        disposition=assessment.disposition,
        accepted=accepted,
        obligation_satisfied=obligation_satisfied,
        reasons=tuple(reasons),
    )


def _has_trajectory_identity(assessment: Assessment) -> bool:
    return (
        _identifying(assessment.assessment_id)
        and _identifying(assessment.claim_id)
        and _identifying(assessment.family)
        and _identifying(assessment.authority.identifier)
        and _identifying(assessment.authority.immutable_revision)
        and assessment.subject.has_required_context()
    )


def establish_trajectory(
    before: Assessment,
    after: Assessment,
    facts: TrajectoryFacts,
) -> TrajectoryResult:
    reasons = []
    if not _has_trajectory_identity(before):
        reasons.append("invalid_before_identity")
    if not _has_trajectory_identity(after):
        reasons.append("invalid_after_identity")
    if before.claim_id != after.claim_id:
        reasons.append("different_claim")
    if before.family != after.family:
        reasons.append("different_family")
    if before.authority != after.authority:
        reasons.append("different_normative_authority")
    if before.subject.kind != after.subject.kind or before.subject.identifier != after.subject.identifier:
        reasons.append("different_subject")
    if not facts.comparable:
        reasons.append("insufficient_comparability")
    if not facts.exact_property_changed:
        reasons.append("property_change_not_established")

    established = not reasons
    return TrajectoryResult(
        established=established,
        direction=facts.direction if established else None,
        change_bases=facts.change_bases,
        history_relation=facts.history_relation,
        reasons=tuple(reasons),
    )
