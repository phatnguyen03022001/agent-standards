# Assessment Kernel Candidate

**Status:** `NON_RELEASED_CANDIDATE`  
**Authority:** `NONE`  
**Generation:** `NOT_ASSIGNED`

This sandbox is non-authoritative. Frozen Generation 1 remains the repository's authoritative standards model and enforcement surface; this candidate does not modify or reinterpret it.

The candidate exists only to make a small set of assessment semantics executable and falsifiable. Inputs are explicit structured facts: applicability, an applicable judgment, optional `EXCEPTION` disposition, immutable normative identity, claim-relative material subject context, attributable evidence references with explicitly supported inferences, optional explicit cross-claim dependencies, change bases, history relation, and trajectory facts.

Key boundaries:

- Unknown applicability is not factual non-applicability.
- Only an accepted applicable `PASS` with no exception disposition satisfies the local obligation.
- Evidence must explicitly support the exact asserted inference; no prose, NLP, keyword, confidence, or fuzzy inference exists.
- Subject context is claim-relative; required context is declared by the fixture rather than imposed by a universal domain schema.
- Cross-family judgments stay independent unless the exact claim explicitly carries a dependency.
- Trajectory requires explicit comparability and exact-property change. Change bases are explanatory context and may be multi-causal; no individual basis token is universally required. A changed assessment, better observation, correction, or supersession alone is not substantive improvement or regression.
- Source revision is only one possible subject-context field and is not required to change for substantive trajectory.
- No family, dimension, overall, weighted, percentage, or maturity score/aggregation API exists.

`test_model.py` is the executable boundary for the authorized adversarial regressions. The model has no archetype-driven runtime behavior; archetype labels, when useful, belong only to test-fixture organization.
