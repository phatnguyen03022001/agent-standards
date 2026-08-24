# agent-standards

`agent-standards` is a technology-neutral, evidence-driven engineering maturity standard for deterministic, auditable software assurance.

## V1 status

V1 is frozen at this revision. The public release identity is `v1.0.0` when that tag and GitHub release point to this exact promoted revision. Consumers must pin an exact frozen commit SHA; branch names, tags, and names such as `latest` are convenience pointers, not normative identities.

## Boundary

Standards define engineering properties. Architect chooses mechanisms. Project documentation records decisions. Targets implement them. Evidence proves them.

This repository owns the maturity model and its engineering assurance semantics. It does not own target architecture, product decisions, domain truth, target profiles, exceptions, or assessment results.

## Dimensions

V1 contains 14 dimensions:

- **COR — Correctness:** intended behavior and state invariants.
- **SEC — Security:** protection across trust and authority boundaries.
- **PRI — Privacy:** handling of personal or privacy-sensitive information.
- **DAT — Data Integrity:** integrity across storage, transmission, transformation, and persistence boundaries.
- **REL — Reliability & Resilience:** bounded failure, recovery, and sustained service behavior.
- **PER — Performance & Scalability:** bounded performance across relevant operating conditions.
- **OBS — Observability:** attributable evidence for state, behavior, and failure diagnosis.
- **MNT — Maintainability & Changeability:** controlled, understandable, and isolated change.
- **OPS — Operability & Delivery:** safe operation, deployment, rollback, and recovery.
- **CMP — Compatibility & Portability:** controlled compatibility and environment assumptions.
- **SUP — Dependency & Supply-Chain Integrity:** controlled dependencies, construction inputs, and provenance.
- **EFF — Resource & Cost Efficiency:** bounded resource and cost behavior.
- **ASR — Assurance & Verification:** traceable claims, evidence, and independent assurance.
- **SAF — Safety & Harm Containment:** containment of credible severe real-world harm.

## Maturity levels

Levels are cumulative. A higher level cannot bypass an unmet applicable lower-level requirement.

- **0 — UNCONTROLLED:** the Level 1 gate is not completely satisfied.
- **1 — BASIC:** explicit baseline invariants and direct evidence.
- **2 — CONTROLLED:** routine operation and foreseeable failure are bounded and repeatably verified.
- **3 — HARDENED:** important edge, degraded, hostile, overload, concurrency, and dependency conditions are explicitly handled.
- **4 — CRITICAL:** high-impact failures receive stronger containment, recovery, evidence, and independent review.
- **5 — HIGH_ASSURANCE:** exceptional confidence requires rigorous evidence, bounded assumptions, strong containment, and rigorous independence.

## Canonical authority

- `STANDARD_MODEL.md` defines interpretation, levels, statuses, applicability, evidence semantics, identity, revision pinning, and domain boundaries.
- `standards/manifest.yaml` defines standards generation and the dimension registry.
- `standards/*.yaml` contain the canonical requirement statements, applicability, and evidence obligations.
- `tools/validate.py` and the tests are enforcement aids. They do not replace or override the normative sources.

## Validation

```bash
python -m pip install -r requirements-validator.txt
python tools/validate.py
python -m unittest discover -s tests -v
```

## License

Apache-2.0.
