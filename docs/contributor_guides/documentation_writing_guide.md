# Documentation Writing Guide

Use this as a short checklist when updating docs.

Guide hierarchy:
- this page (writing conventions) points to the
  [Documentation Automation Guide](documentation_automation_guide.md) for
  execution workflow;
- the automation guide then points to `scripts/README.md` for generator internals.

## 1) Keep Responsibilities Clear

- `Schema Navigation` (generated): structure, quantities, relationships.
- `Schema Explanation` (hand-written): schema understanding, rationale, invariants, traversal, and usage of existing schema components.
- `Schema Development` (hand-written): implementation guidance for schema extenders, parser authors, and contributors writing schema-related code.
- `Contribution Guides` (within Schema Development): overarching process, writing, and automation instructions.
- `.dev_notes/` (internal): history, design rationale, implementation limits, migration traps, and agent-facing technical context.
- Do not duplicate generated reference content in explanation pages.
- Add canonical links to relevant `schema/*.md` pages for backlink discovery
  (see [Automation Guide](documentation_automation_guide.md#auto-discovered-backlinks-to-explanation-pages)).

### Placement Rules

- Put a page in `Schema Explanation` when its primary question is: "What does this part of the schema mean, how is it organized, and how should it be understood, instantiated, populated, or traversed?"
- Put a page in `Schema Development` when its primary question is: "How do I implement, extend, populate, migrate, debug, or contribute this in code or parsers?"
- Put a note in `.dev_notes/` when the content is too detailed, provisional, historical, or design-internal for the published docs.
- Mixed pages are allowed, but one audience must be clearly primary. Link to the secondary material instead of duplicating it.

### Snippet Test

- If the key code snippets define new schema classes, quantities, subsections, or `normalize()` implementations, the page likely belongs in `Schema Development`.
- If the key code snippets instantiate, populate, inspect, or traverse existing schema components, the page likely belongs in `Schema Explanation`.

### Normalization Rule

- The mere presence of normalization-related content does **not** automatically make a page a `Schema Development` page.
- Put normalization content in `Schema Explanation` when it explains what existing normalization does, how derived quantities or sections are produced, and how normalized archive content should be interpreted.
- Put normalization content in `Schema Development` when it explains how `normalize()` works as an implementation mechanism, how to write or extend normalization logic, ordering rules, debugging, or other implementation guidance.

### Versioning and History Rule

- Published docs should describe the current schema state rather than narrate repository history.
- Avoid phrases such as "recent refactoring", "previously", "used to", "old schema", or similar comparisons unless a page is explicitly about a supported version transition.
- Prefer describing the current semantics directly: explain what a field means, what is derived, and how archive data should be interpreted now.
- Only document migration or version-to-version differences when there is an explicit supported transition between named schema versions (for example, major versions with active user impact).
- Keep detailed design history, repository evolution, and unversioned migration context out of forward-facing docs.

## 2) Keep Pages Focused

- Define a single primary question each page answers (for example:
  "how to model `ModelSystem` hierarchy").
- Move secondary material to linked pages instead of expanding scope.
- If two pages repeat more than a short paragraph, keep one canonical version
  and replace the duplicate with a link.
- Prefer short sections with explicit headings.

## 3) Implementation Docs Workflow

When an implementation introduces a new documentation set:

1. Decide whether content belongs in published docs or internal notes:
  use `docs/explanation/*` for published schema-understanding pages,
  `docs/schema_development/*` for published implementation/development pages,
  and move implementation/TODO/history-heavy notes to `.dev_notes/`.
2. Keep explanation pages focused on rationale, traversal, and usage patterns of existing schema components.
  Keep development pages focused on implementation patterns, extension points, migrations, and code-level guidance.
  Remove duplicated structure/quantity/class inventory content once auto-doc
  pages exist (auto-generated content lives in `docs/schema/*`, not in hand-written pages).
  Avoid explaining the schema through unversioned historical comparisons; prefer current-state descriptions.
3. For auto-doc navigation decisions, see
   [Automation Guide](documentation_automation_guide.md#guidelines-for-adding-auto-doc-navigation).

## 4) Use a Simple Page Pattern

Use this structure for technical explanation pages (not required for
overview/landing pages):

1. Purpose
2. Link to generated page(s)
3. Rules/invariants
4. Usage guidance (instantiating, populating, inspecting, or traversing existing schema)
5. Pitfalls and related links

For technical development pages, use a parallel pattern:

1. Purpose
2. Audience / when to use this guide
3. Implementation pattern or extension point
4. Executable examples
5. Pitfalls, migrations, and related links

For both explanation and development pages, describe the current schema first.
Only add migration/version sections when there is an explicit supported version transition that readers need to handle.

## 5) Keep Examples Executable

- Store snippets in `docs/snippets/`.
- Include snippets via `--8<-- "snippets/<path>/<file>.py"`.
- Mark standalone runnable snippets with `# docs-snippet: runnable`.
- Ensure every snippet has test coverage in `tests/test_doc_snippets.py`.
- See `docs/snippets/README.md` for snippet categories and markers.

## 6) Assets and Paths

- Store page-specific images in a local `images/` folder.
- Reference with `./images/<file>` whenever possible.

## 7) Before Opening a PR

- For schema changes, see regeneration requirements in
  [Automation Guide](documentation_automation_guide.md#4-ownership-and-update-rules).
- Update only affected explanation pages.
- Verify links and docs build (`mkdocs build`).
