# agent-standards

`agent-standards` defines a candidate, technology-neutral engineering maturity model. **V1-CANDIDATE-1 is not frozen or released.** Candidate work lives on `dev`; `main` remains the bootstrap root until a separately approved release.

Normative authority is split deliberately:

- `STANDARD_MODEL.md` defines interpretation, levels, statuses, applicability, evidence semantics, identity, revision pinning, and domain boundaries.
- `standards/manifest.yaml` defines the generation and dimension registry.
- `standards/*.yaml` contain the canonical requirement statements and evidence obligations.
- `tools/validate.py` and tests are derived enforcement aids; they never override normative sources.

Consumers must pin an exact frozen commit SHA. Branches, tags, and names such as `latest` are not normative revisions. Until V1 is frozen, do not use this candidate as a released assessment standard.

## Candidate validation

```bash
python -m pip install -r requirements-validator.txt
python tools/validate.py
python -m unittest discover -s tests -v
```

The candidate contains 14 dimensions: COR, SEC, PRI, DAT, REL, PER, OBS, MNT, OPS, CMP, SUP, EFF, ASR, and SAF. Numeric maturity is cumulative from Level 1 through Level 5; wholly inapplicable dimensions report `N/A`, not a numeric level.

This repository stores no target profiles, target exceptions, assessment results, domain truth, workflow engine, CI configuration, or runtime orchestration.
