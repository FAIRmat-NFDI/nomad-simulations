# Model System Patterns

This page captures reusable modeling patterns for `ModelSystem` and related sections.
It is intentionally cross-cutting and should be referenced by focused pages such as `Model System` and `Representation Architecture`.

## Pattern 1: One Representative System per Simulation Context

Use one `ModelSystem` as the representative system for a calculation context.

- Set `is_representative=True` only on the system that should trigger full normalization logic.
- Keep derived or contextual subsystems non-representative unless there is a clear reason to normalize them independently.

Why this matters:

- prevents duplicate normalization side effects,
- keeps formula/symmetry derivations deterministic,
- clarifies provenance of the primary structure.

## Pattern 2: Vertical vs Lateral Structure

There are two orthogonal ways to organize system information:

- vertical hierarchy: `sub_systems` (`ModelSystem` -> `ModelSystem`) for decomposition into regions/components,
- lateral variants: `representations` (`ModelSystem` -> `AlternativeRepresentation`) for alternate geometric views of the same physical system.

Use `sub_systems` for physical parts of a system.
Use `representations` for equivalent geometric descriptions (primitive/conventional/supercell) of one system.

## Pattern 3: Original Data on Root, Derived Data in Alternatives

Store parser-native geometry directly on the main `ModelSystem`.
Store generated or transformed views in `representations`.

Recommended assignment order in parsers:

1. set direct geometry (`lattice_vectors`, `positions`, `periodic_boundary_conditions`) on `ModelSystem`,
2. add `particle_states`,
3. add derived/standardized geometry as `AlternativeRepresentation` entries,
4. run normalization in NOMAD context.

This keeps raw input and derived views clearly separated.

## Pattern 4: Reference by Identity, Not by Duplication

When connecting properties/methods to a system, prefer references to relevant sections over duplicating system descriptors.

- Keep structural descriptors in `ModelSystem`.
- Refer to them from outputs/method sections where needed.

This avoids drift between repeated copies of conceptually identical data.

## Pattern 5: Normalize for Completion, Not for Reconstruction

Normalization should:

- complete missing derived descriptors,
- validate consistency,
- enrich discoverability.

Normalization should not:

- silently replace parser intent,
- require inferred assumptions that are not universally valid.

In practice, parser-side explicitness should win when information is available.

## Pattern 6: Document Invariants Next to Usage

For maintainability, every explanation page touching `ModelSystem` should explicitly state invariants it depends on, such as:

- representative-system assumptions,
- coordinate conventions,
- how subsystem indices map to parent particle indices,
- whether a transformation is semantic or merely representational.

When these invariants change, update all linked explanation pages in the same PR.
