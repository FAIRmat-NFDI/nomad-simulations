# Schema Explanation Overview

`Schema Navigation` and `Schema Explanation` have different responsibilities:

- `Schema Navigation` (auto-generated): canonical source for section trees, quantities, inheritance, and relationship diagrams.
- `Schema Explanation` (hand-written): design rationale, modeling decisions, migration notes, parser guidance, and cross-cutting usage patterns.

Use both together:

1. Start in `Schema Navigation` to find section/quantity definitions.
2. Open `Schema Explanation` when you need to understand why the schema is modeled that way or how to use it consistently.

## Where to Find What

- `Schema Navigation > Simulation Entry`: structure and quantities for `Simulation` and direct children.
- `Schema Navigation > Model System`: class graph and quantity-level reference for system-related sections.
- `Schema Navigation > Model Method`: class graph and quantity-level reference for method and numerical settings.
- `Schema Navigation > Outputs`: class graph and quantity-level reference for output/property sections.

- `Schema Explanation > Model System`: conceptual usage patterns and modeling tradeoffs.
- `Schema Explanation > Model Method`: domain-specific method explanations (for example basis set families).
- `Schema Explanation > Bounded Data Types`: bounded numeric types and serialization caveats.
- `Schema Explanation > Normalization`: execution model and common normalization patterns.

## Scope Rules for Hand-Written Pages

Hand-written pages should prioritize:

- intent and design constraints,
- usage patterns and examples,
- migration guidance and known pitfalls,
- extension and contribution guidance.

Hand-written pages should avoid duplicating:

- exhaustive quantity tables,
- generated class relationship diagrams,
- field-by-field API reference content.

