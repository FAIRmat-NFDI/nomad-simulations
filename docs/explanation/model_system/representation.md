# Representation Architecture

`Representation` captures geometric description conventions for model systems.
For full quantity and class reference, use the generated page: [Schema Navigation: Alternative Representations](../../schema/representations.md).

This page focuses on architecture-level intent and usage guidance.

## Core Design Decision

Primary geometry lives directly on `ModelSystem`.
Alternative geometric views live in `ModelSystem.representations` as `AlternativeRepresentation` entries.

This gives:

- one canonical source for parser-native geometry,
- explicit provenance for transformed/derived cell descriptions,
- less ambiguity than storing multiple competing geometries in one flat structure.

See [Model System Patterns](patterns.md) for the reusable rule set used across related docs.

## Coordinate and Transformation Semantics

Representations are different parameterizations of the same physical system.

- They may differ in lattice basis choice and fractional coordinate mapping.
- They should not be treated as distinct physical subsystems.

When transformations are provided (`transformation_matrix`, `origin_shift`), document whether they come directly from upstream tooling (for example symmetry analysis output) or parser-side transforms.

## Parser Guidance

Recommended parser flow:

1. assign parser-native geometry to the root `ModelSystem`,
2. append derived/standardized representations to `representations`,
3. keep naming explicit (`primitive`, `conventional`, domain-specific names),
4. avoid creating alternatives when only one geometry exists.

Minimal example:

```python
--8<-- "snippets/model_system/alternative_representation_pattern.py"
```

## Anti-Patterns

- storing parser-native and derived geometry as indistinguishable peers,
- encoding subsystem decomposition through `representations`,
- duplicating full geometry across docs without explaining the modeling intent.

## Change Management

If representation behavior changes (new invariants, naming conventions, normalization behavior), update:

1. this page (architecture intent),
2. [Model System Patterns](patterns.md) (shared rules),
3. relevant generated schema pages via the docs pipeline.
