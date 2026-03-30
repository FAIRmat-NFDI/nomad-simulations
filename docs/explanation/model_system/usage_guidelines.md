# Model System Schema Usage Guidelines

## Required Rules

1. Exactly one representative system per simulation context.
Do: set `is_representative=True` only on the primary system.
Do not: mark derived/contextual systems representative by default.
Reference: [Model System](overview.md), [Normalization](../normalize.md)

2. Keep vertical and lateral structure separate.
Do: use `sub_systems` for physical decomposition (`ModelSystem -> ModelSystem`).
Do: use `representations` for alternative geometric views (`ModelSystem -> AlternativeRepresentation`).
Do not: encode hierarchy inside `representations` or alternatives inside `sub_systems`.
Reference: [Model System](model_system.md), [Representation Architecture](representation.md)

3. Keep parser-native geometry on the root system.
Do: store original parser geometry directly on the root `ModelSystem`.
Do: store generated/transformed variants in `representations`.
Do not: overwrite parser-native geometry during normalization.
Reference: [Representation Architecture](representation.md), [Normalization](../normalize.md)

4. Reuse structure by reference instead of duplication.
Do: define structural descriptors once in `ModelSystem`.
Do: reference those sections from methods/outputs where possible.
Do not: duplicate equivalent structural data across branches.
Reference: [Model System](overview.md)

5. Use normalization for completion and validation.
Do: derive missing descriptors and run consistency checks.
Do not: silently rewrite explicit parser intent.
Reference: [Normalization](../normalize.md)

6. Keep documentation invariants synchronized.
Do: update affected explanation pages in the same PR when usage rules change.
Do: keep this page as policy-only and move long examples elsewhere.
Reference: [Model System](overview.md), [Representation Architecture](representation.md), [Documentation Writing Guide](../../contributor_guides/documentation_writing_guide.md)

!!! info "Contributor Note"
    This page defines required usage rules for `ModelSystem` and should stay
    concise. Keep long implementation details and extended examples in linked
    pages.
