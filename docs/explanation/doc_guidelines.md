# Documentation Authoring Guide

This guide defines how to keep `Schema Navigation` (generated) and `Schema Explanation` (hand-written) complementary and maintainable.

## Source of Truth Split

- Generated (`Schema Navigation`) is the source of truth for:
  - section/quantity listings,
  - relationship maps,
  - inheritance and containment structure,
  - meta-info links.

- Hand-written (`Schema Explanation`) is the source of truth for:
  - design rationale,
  - modeling constraints and invariants,
  - parser/normalization usage patterns,
  - migration notes and known pitfalls,
  - extension guidance.

## What to Include

Include content that answers:

- Why is this schema concept modeled this way?
- What invariants must remain true?
- Which parser vs normalization responsibilities apply?
- What common mistakes should contributors avoid?
- How should future extensions stay consistent?

## What Not to Include

Do not add to hand-written pages:

- full quantity tables already generated,
- generated relationship diagrams copied by hand,
- exhaustive API references,
- repeated definitions of the same class/quantity across multiple pages.

Instead, link to generated pages in `Schema Navigation`.

## Page Template (Recommended)

Use this structure for new hand-written pages:

1. Purpose and scope
2. Link to generated reference page(s)
3. Design constraints/invariants
4. Usage patterns (parser/normalization)
5. Anti-patterns or pitfalls
6. Migration notes (if relevant)
7. Related pages

Keep examples minimal and illustrative.
Use one canonical example per concept, not many variations of the same pattern.

## Modularization Rules

- Put cross-cutting rules in one shared page and link to it.
- Keep domain pages focused on one concern each.
- Prefer short sections with explicit headings over long narrative blocks.
- If two pages repeat the same 2+ paragraphs, extract them into a shared page.

## Update Workflow for Schema Changes

When schema structure changes:

1. update schema code,
2. run docs generation pipeline (`scripts/generate_docs_pipeline.py`),
3. update only impacted explanation pages,
4. check nav labels/paths in `mkdocs.yml`,
5. verify links and build docs locally.

## PR Checklist for Docs

Before merging a docs PR, verify:

- [ ] no duplicated field-level reference content between generated and hand-written pages,
- [ ] new explanation content states rationale/invariants, not only structure,
- [ ] shared patterns page updated when introducing cross-cutting rules,
- [ ] `mkdocs.yml` navigation remains coherent,
- [ ] internal links resolve,
- [ ] examples are small and aligned with current schema behavior.
