# Documentation Writing Guide

Use this as a short checklist when updating docs.

Guide hierarchy:
- this page (writing conventions) points to the
  [Documentation Automation Guide](documentation_automation_guide.md) for
  execution workflow;
- the automation guide then points to `scripts/README.md` for generator internals.

## 1) Keep Responsibilities Clear

- `Schema Navigation` (generated): structure, quantities, relationships.
- `Schema Explanation` (hand-written): rationale, invariants, usage guidance.
- Do not duplicate generated reference content in explanation pages.
- Add canonical links to relevant `schema/*.md` pages for backlink discovery
  (see [Automation Guide](documentation_automation_guide.md#auto-discovered-backlinks-to-explanation-pages)).

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
   use `docs/explanation/*` (Schema Explanation section) for user/contributor-facing guidance, and move
   implementation/TODO/history-heavy notes to `.dev_notes/` (or `.dev_docs/`
   if that internal folder is adopted in the repository).
2. Keep explanation pages focused on rationale, traversal, and usage patterns.
   Remove duplicated structure/quantity/class inventory content once auto-doc
   pages exist (auto-generated content lives in `docs/schema/*`, not `docs/explanation/*`).
3. For auto-doc navigation decisions, see
   [Automation Guide](documentation_automation_guide.md#guidelines-for-adding-auto-doc-navigation).

## 4) Use a Simple Page Pattern

Use this structure for technical explanation pages (not required for
overview/landing pages):

1. Purpose
2. Link to generated page(s)
3. Rules/invariants
4. Usage guidance (parser/normalization)
5. Pitfalls and related links

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
