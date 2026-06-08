# Model Method Overview

## Pages in This Section

- [Basis Sets](basis_sets.md)

## Schema Navigation References

- [Model Method](../../schema/model_method.md)
- [Force Field](../../schema/force_field.md)
- [Model Method Electronic](../../schema/model_method_electronic.md)
- [Numerical Settings](../../schema/numerical_settings.md)

## Purpose

This page explains how method information is organized in the
`ModelMethod` hierarchy and how to read that structure within a NOMAD archive.

For full section and quantity definitions, use the schema navigation references
above.

## Reading the Hierarchy

- Method identity is expressed by fields such as `name`, `type`, and the
  relevant method-family quantities.
- Numerical realization remains attached through `numerical_settings`, so the
  method description and its practical setup remain connected without being
  merged into the same conceptual layer.
- Additive terms are commonly represented through `contributions`, which keeps
  composite methods readable as structured combinations rather than flattened
  lists of unrelated quantities.

## Hierarchy Snapshot

--8<-- "snippets/generated/model_method_hierarchy.md"

## Key Method Families

--8<-- "snippets/generated/model_method_family_map.md"

## Interpreting Method Data in Archives

- Method identity is carried by fields such as `name`, `type`, and the relevant
  method-family quantities.
- Numerical realization remains attached through `numerical_settings`, so
  archive readers can distinguish model semantics from solver/setup choices.
- References to related `ModelSystem` or `Outputs` sections are best
  understood as links between archive components rather than duplicated method
  descriptions.

## Example

```python
--8<-- "snippets/model_method/model_method_overview_example.py"
```

## Related Pages

- [Basis Sets](basis_sets.md)
- [ModelMethod vs NumericalSettings](../../schema_development/model_method_vs_numerical_settings.md)
