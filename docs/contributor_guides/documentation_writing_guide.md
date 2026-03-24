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
- Add canonical links to relevant `schema/*.md` pages so generated schema docs
  can auto-link back to explanations.
- Keep manually written workflow guides under `docs/explanation/workflow/`
  (not under `docs/schema/`).

## 2) Keep Pages Focused

- Define a single primary question each page answers (for example:
  "how to model `ModelSystem` hierarchy").
- Move secondary material to linked pages instead of expanding scope.
- If two pages repeat more than a short paragraph, keep one canonical version
  and replace the duplicate with a link.
- Prefer short sections with explicit headings.

## 3) Implementation Docs Workflow

When an implementation introduces a new documentation set:

1. Place docs under `Schema Explanation` by default.
2. Do not manually edit navigation as a first step.
3. If generated/auto-doc scope grows, consider adding an auto-doc navigation
   section (see guidelines below).
4. Remove duplicated structure/quantity/class inventory content from
   explanation pages once auto-doc pages exist; keep explanation pages focused
   on rationale, traversal, and usage patterns.
5. Decide whether content belongs in published docs or internal notes:
   use `docs/explanation/*` for user/contributor-facing guidance, and move
   implementation/TODO/history-heavy notes to `.dev_notes/` (or `.dev_docs/`
   if that internal folder is adopted in the repository).

Guidelines for adding an auto-doc navigation section:

- Add a dedicated auto-doc section when the scope is medium/large (roughly
  3+ generated pages or a full schema subdomain with inheritance/relations).
- Add it when the content is schema-structural and expected to evolve through
  introspection/generation (not hand-maintained prose).
- Keep top-level section ordering consistent with schema structure.
- Keep child pages root-first, then deterministic ordering (currently
  alphabetical by title unless a documented override applies).
- Implement navigation through generation scripts/source-of-truth
  (`scripts/verticals.py` and docs pipeline), not by hand-editing generated
  navigation blocks.

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

- Run the docs generation pipeline if schema structure changed.
- Update only affected explanation pages.
- Check `mkdocs.yml` navigation paths/titles.
- Verify links and docs build.
