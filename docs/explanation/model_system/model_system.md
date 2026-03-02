# Model System

`ModelSystem` represents the physical system used in a simulation context.
For canonical quantity-level reference (fields, types, full relation map), use the generated page: [Schema Navigation: Model System](../../schema/model_system.md).

This page focuses on intent, usage boundaries, and composition patterns.

## What `ModelSystem` Owns

`ModelSystem` is the owner of structural system information:

- system-level geometry,
- particle-state membership,
- subsystem hierarchy,
- links to symmetry and chemical formula descriptors,
- links to alternative geometric representations.

`ModelSystem` is therefore the canonical location for "what system was simulated".

## Structural Semantics

Use `ModelSystem` to express two different relationships:

- decomposition: `sub_systems` creates a parent-child system tree,
- alternative views: `representations` stores equivalent geometric variants of the same system.

Do not mix these semantics.
A subsystem is a different component; an alternative representation is the same component viewed differently.

See [Model System Schema Usage Guidelines](usage_guidelines.md) for reusable design rules.

## Parser and Normalization Responsibilities

Recommended split:

- parser responsibilities:
  - populate primary system geometry and particle states,
  - populate explicit subsystem composition,
  - add available method/system references.
- normalization responsibilities:
  - compute derived descriptors (for example symmetry and formulas),
  - validate consistency,
  - enrich metadata needed for search and interoperability.

For normalization execution order and mechanics, see [Normalization](../normalize.md).

## Minimal Parser Pattern

```python
--8<-- "snippets/model_system/minimal_parser_pattern.py"
```

Add subsystem composition only when physically meaningful for analysis.
Avoid creating hierarchy levels that do not encode new semantics.

## Extension Guidance

When adding new `ModelSystem`-related documentation:

- keep field-level reference in generated docs,
- keep explanation docs focused on modeling constraints and usage decisions,
- link to shared schema usage guidelines instead of repeating conventions,
- include migration notes when behavior changes.
