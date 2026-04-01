# Model Method Overview

## Pages in This Section

- [ModelMethod vs NumericalSettings](model_method_vs_numerical_settings.md)
- [Basis Sets](basis_sets.md)

## Schema Navigation References

- [Model Method](../../schema/model_method.md)
- [Force Field](../../schema/force_field.md)
- [Model Method Electronic](../../schema/model_method_electronic.md)
- [Numerical Settings](../../schema/numerical_settings.md)

## Purpose

This page explains how to use the `ModelMethod` hierarchy in hand-written
schema data, without duplicating generated structure tables.

For full section and quantity definitions, use the schema navigation references
above.

## Rules and Invariants

- Use `name`/`type` to identify the method family and subtype.
- Keep Hamiltonian/model semantics in `ModelMethod` and subclasses.
- Keep numerical control parameters under `numerical_settings`.
- Use `contributions` for additive model terms instead of flattening all terms
  into one section.
- When a concept has both a physical-model aspect and an implementation aspect,
  split them: keep the model identity in `ModelMethod` and the realization knobs
  in `NumericalSettings`.

## Hierarchy Snapshot

--8<-- "snippets/generated/model_method_hierarchy.md"

## Key Method Families

--8<-- "snippets/generated/model_method_family_map.md"

## Archive Population and Cross-Linking Guidance

- Prefer explicit population of method-defining fields.
- Use normalization to complete derived or cross-linked information, not to
  overwrite explicitly provided method identity.
- Keep references to `ModelSystem`/`Outputs` sections by identity rather than
  data duplication.

## Executable Example

```python
--8<-- "snippets/model_method/model_method_overview_example.py"
```

## Related Pages

- [ModelMethod vs NumericalSettings](model_method_vs_numerical_settings.md)
- [Basis Sets](basis_sets.md)
- [Model System Usage Guidelines](../../schema_development/model_system_usage_guidelines.md)
- [Normalization](../../schema_development/normalize.md)
