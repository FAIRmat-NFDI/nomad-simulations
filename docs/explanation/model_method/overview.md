# Model Method Overview

## Purpose

This page explains how to use the `ModelMethod` hierarchy in hand-written
schema data, without duplicating generated structure tables.

For full section and quantity definitions, use:

- [Model Method (Schema Navigation)](../../schema/model_method.md)
- [Model Method Electronic (Schema Navigation)](../../schema/model_method_electronic.md)
- [Numerical Settings (Schema Navigation)](../../schema/numerical_settings.md)
- [Force Field (Schema Navigation)](../../schema/force_field.md)
- [ModelMethod vs NumericalSettings](model_method_vs_numerical_settings.md)

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

## Parser and Normalization Guidance

- Prefer explicit parser population of method-defining fields.
- Use normalization to complete derived or cross-linked information, not to
  overwrite explicit parser intent.
- Keep references to `ModelSystem`/`Outputs` sections by identity rather than
  data duplication.

## Executable Example

```python
--8<-- "snippets/model_method/model_method_overview_example.py"
```

## Related Pages

- [ModelMethod vs NumericalSettings](model_method_vs_numerical_settings.md)
- [Basis Sets](basis_sets.md)
- [Model System Usage Guidelines](../model_system/usage_guidelines.md)
- [Normalization](../normalize.md)
