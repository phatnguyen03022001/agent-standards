# Standard Model — V1 Candidate

**Status:** candidate only; not frozen. Requirement text is canonical only in `standards/*.yaml`.

## Levels

Numeric levels are normative; labels are stable shorthand.

- **0 — UNCONTROLLED:** no meaningful guarantee; the Level 1 gate is not completely satisfied. Level 0 has no requirement IDs.
- **1 — BASIC:** expected-use behavior has explicit invariants, obvious failures are bounded, and direct evidence exists.
- **2 — CONTROLLED:** normal real-world operation and foreseeable routine failure are bounded and repeatably verified.
- **3 — HARDENED:** important edge, degraded, hostile, overload, concurrency, dependency, and adversarial conditions are explicitly handled; containment is first-class.
- **4 — CRITICAL:** high-impact failures receive strong containment, recovery, defense-in-depth, strong evidence, and genuine independent review.
- **5 — HIGH_ASSURANCE:** exceptional confidence rests on strong direct evidence, explicit assumptions, rigorous containment, and independent reproduction or equivalent rigorous independence suitable for high-consequence systems.

Level 5 may be expensive and must not be weakened merely to make it easy to claim.

## Cumulative achievement

For an applicable dimension, the achieved level is the maximum `N` such that every applicable requirement whose level is at most `N` is `PASS`. Valid requirement-level `N/A` items are removed from the applicable set. `PARTIAL`, `GAP`, `UNKNOWN`, and `EXCEPTION` block their level and every higher level. Higher-level PASS results never compensate for a lower-level blocker. Never report fractional levels, percentages, averages, or points.

Examples: PASS through Level 1 plus a Level 2 GAP yields Level 1; replacing GAP with UNKNOWN, PARTIAL, or EXCEPTION still yields Level 1. A Level 3 PASS cannot bypass that Level 2 blocker. A wholly inapplicable dimension reports `N/A`, never Level 5.

## Status vocabulary

- **PASS:** the requirement applies and all property and evidence obligations are satisfied for the assessed scope and revision.
- **PARTIAL:** only part of the required property, scope, or evidence is established; it does not contribute.
- **GAP:** evidence establishes non-conformance.
- **UNKNOWN:** applicability or satisfaction cannot be established with sufficient attributable evidence. Missing, stale, contradictory, inaccessible, or untied evidence is never PASS.
- **N/A:** the canonical conditional applicability predicate is demonstrably false. It is excluded, not passed. An `always` requirement can never be N/A.
- **EXCEPTION:** the requirement applies and is intentionally unmet under explicit bounded risk acceptance. It remains unmet for maturity.

N/A requires a conditional predicate, target facts proving it false, and explicit rationale. Risk acceptance is EXCEPTION, not N/A. Lack of evidence is UNKNOWN.

Target-owned exception records should identify requirement ID, affected scope, known non-conformance, consequence, accepting authority, rationale, acceptance date, and review/expiry boundary or an explicit reason for no expiry. Exceptions never rewrite this standard.

## Requirement model

YAML is canonical. Each requirement has exactly `id`, `level`, `statement`, `intent`, `applicability`, and `evidence`. Statements are technology-neutral, determinate, directly verifiable engineering invariants rather than implementation prescriptions. Normative requirements constrain engineering properties rather than target architecture, framework, database, cloud, protocol, infrastructure, or design-pattern choices unless an applicable externally-owned constraint itself requires a specific mechanism. Intent explains the failure class.

Applicability is either `mode: always` or `mode: conditional` with at least one factual predicate in `all_of` and/or `any_of`. For conditional applicability, all `all_of` predicates must be true and, when `any_of` exists, at least one `any_of` predicate must be true. Predicates describe observable target facts, not vague discretion. Applicability conditions belong only in this canonical structure; an `always` requirement must not create an N/A escape hatch with prose such as “where applicable”, “where relevant”, “when appropriate”, or equivalent discretionary wording.

Applicability truth is determined by the underlying target facts, not by whether the target has already documented, identified, inventoried, attributed, or traced those facts. Documentation, identification, inventory completeness, attribution, and traceability are substantive or evidence obligations rather than conditions that create applicability. If the truth of a conditional predicate cannot be established from sufficient attributable evidence, the requirement is `UNKNOWN`, not `N/A`; `N/A` requires evidence that the factual predicate is false. Omission from an inventory, hazard model, or other target-owned record cannot make an otherwise applicable externally-owned constraint inapplicable.

Evidence contains a nonempty `required` list. Each obligation has `demonstrates` and one or more allowed `classes`; every obligation is required, while any one listed class can satisfy an obligation. `independence` is exactly `none`, `independent_review`, or `independent_reproduction`.

## Non-vacuous Level 4 and Level 5 scope

Level 4 and Level 5 scope-selection terms such as `material`, `high-impact`, `critical`, `consequential`, `major`, `significant`, `representative`, and `strongest claimed` identify the portion of an applicable dimension that receives stronger assurance. They are not optional escape clauses and do not permit an applicable dimension to declare an empty high-consequence scope merely because the target has not created a class carrying one of those labels.

For every applicable dimension, the assessor and target must identify the in-scope properties, assets, operations, failure modes, or claims having the highest consequence within that dimension. When no separately designated “critical”, “major”, or equivalent class exists, Level 4 and Level 5 requirements apply to the highest-consequence material applicable subset rather than to an empty set. The classification rationale and the facts supporting inclusion and exclusion must be explicit and evidence-based; this model does not require or define a numerical severity or risk score.

At Levels 4 and 5, the required independent verifier is permitted to challenge the consequence classification, the selected subset, and exclusions that would improperly narrow the claimed scope. A project cannot use N/A merely because it has not labeled anything “critical”, “high-impact”, or similar. If the consequence classification or the highest-consequence applicable subset cannot itself be established with sufficient evidence, the affected high-level requirement is `UNKNOWN`, not PASS or N/A.

These scope rules select evidence and verification depth within an already applicable dimension. They do not replace the canonical requirement applicability predicates and do not make target-defined risk acceptance a basis for N/A.

## Evidence semantics

Allowed classes are:

- `artifact_inspection`: direct inspection of source, configuration, specification, generated artifacts, records, or other static state; static evidence cannot prove runtime behavior merely by describing it.
- `analysis`: direct reasoned or mechanical analysis of implementation, architecture, state, or behavior.
- `reproducible_test`: repeatable execution with defined setup, stimulus, oracle, and observable result tied to the claimed scope.
- `runtime_observation`: attributable evidence from representative execution or operation.
- `operational_exercise`: controlled recovery, rollback, failover, incident, restoration, hazardous-state, or disaster exercise.
- `provenance_attestation`: verifiable origin, integrity, lineage, dependency provenance, or equivalent supply-chain evidence.
- `formal_verification`: mathematically rigorous proof, model checking, or equivalent method with explicit assumptions.

There is no numerical evidence-quality score. Evidence is sufficient or insufficient for a requirement. It must be relevant, attributable to the exact revision, scoped to dependent configuration/environment, direct enough for the requested class, reproducible when required, independent to the requested degree, and free of unresolved contradiction. A technology name is not evidence. A policy document is not runtime proof. A screenshot of an unidentified passing test cannot substitute for a reproducible test.

A static structure claim may be established by `artifact_inspection`, `analysis`, or another class that directly proves the static invariant. A runtime enforcement claim must include a mandatory obligation satisfiable only by a runtime-capable or logically equivalent class such as `reproducible_test`, `runtime_observation`, `operational_exercise`, or `formal_verification`. When a requirement needs both a static fact and a runtime fact, they are separate mandatory evidence obligations; satisfying one does not substitute for the other.

`independent_review` requires a verifier to evaluate direct underlying evidence rather than repeat the implementer's assertion. `independent_reproduction` requires an independent verifier to reproduce or independently derive the evidence. Independence concerns verification authority/method, not whether the verifier is human or automated. A target cannot self-certify an independence obligation merely by relabeling its own assertion or evidence producer.

## Dimension applicability

Normally universal: COR, REL, PER, OBS, MNT, OPS, CMP, SUP, EFF, ASR.

Dimension-level conditional:

- SEC applies when a material trust boundary, authority boundary, security-sensitive asset, privileged operation, or attacker-controlled interaction exists.
- PRI applies when the system observes, derives, stores, transmits, exposes, or acts on personal or privacy-sensitive information.
- DAT applies when material data crosses a storage, transmission, persistence, replication, transformation, or integrity boundary.
- SAF applies when output or action can directly cause or materially increase credible severe real-world harm beyond ordinary service, confidentiality, or correctness loss.

Every applicable dimension has an unconditional Level 1 baseline once the dimension itself applies.

## Identity and permanence

Requirement IDs are `<CODE>-<LEVEL>.<SEQUENCE>`. CODE is the registered three-character dimension code; LEVEL is 1–5; SEQUENCE is a positive decimal integer without leading zeroes. IDs are globally unique, must match their owning dimension and level, carry no priority, may contain gaps, and never encode products or technologies. Do not renumber to close gaps.

Once an ID appears in a published candidate SHA, it is not reused for a materially different property. Before freeze, material edits may replace, split, or remove IDs with candidate disclosure. After V1 freeze, V1 meanings do not change; incompatible evolution requires a later standards generation.

An assessment is interpretable only when it pins the standards to an exact frozen commit SHA. `main`, `dev`, tags such as `v1`, and `latest` are convenience pointers, not normative revision identities.

## Canonical ownership

`standards/manifest.yaml` owns generation number, dimension codes, keys, names, and filenames. Dimension YAML owns dimension applicability and all requirement IDs, levels, statements, intents, applicability, and evidence obligations. This document owns interpretation semantics. README is orientation only. Validator/tests are derived enforcement aids. Any mismatch between enforcement and normative sources is a release-blocking defect.

## Domain boundary and external constraints

External and domain truth remains owned by the target or competent domain authority. Generic standards may require those constraints to be identified, traced, enforced, and verified, but `agent-standards` does not invent the constraint itself.

The target must determine which externally-owned engineering or domain constraints apply and preserve their authoritative source or competent owner. ASR owns generic identification and constraint-to-claim-to-evidence traceability. The substantive engineering dimension owns the behavior that implements an identified constraint; for example COR owns behavioral conformance, SAF owns severe-harm containment, and PRI owns privacy behavior. Unresolved applicability, implementation, or verification remains explicitly unresolved rather than disappearing from the claim set.

For example, a product owns its scoring definition and acceptable score behavior; medical authorities own clinical limits; financial authorities or product owners own transaction/risk constraints; aviation authorities and system safety authorities own flight-envelope or operational limits. This model can require exact identified constraints to be enforced and evidenced without declaring the values or domain truth.

## Target-repository relationship

This repository stores no target profiles. A target may conceptually pin `repository` plus an exact frozen `revision` SHA and declare target levels per dimension. The target owns target levels, assessment statuses, evidence references, N/A rationales, exceptions, and domain requirements. `agent-standards` owns only dimension/level/requirement meaning, evidence expectations, and assessment semantics.

## Anti-gaming invariants

No averaging; UNKNOWN is never PASS; N/A requires a false canonical predicate; EXCEPTION is never PASS; higher levels cannot bypass lower blockers; documentation cannot prove runtime behavior; technology names cannot prove properties; Level 4/5 scope cannot be emptied by target labels; Level 5 cannot be self-certified where independent reproduction is required; duplicate controls do not inflate maturity; compound controls must not hide independently fail-able properties; vague discretionary applicability is invalid; and externally-owned constraints cannot be omitted merely because the target failed to inventory them.
