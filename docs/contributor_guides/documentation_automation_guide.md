# Documentation Automation Guide

The docs automation has two responsibilities:

- generate reference pages from schema introspection (`docs/schema/*`),
- generate reusable fragments consumed by hand-written explanation pages.

These are script-driven outputs (not AI-generated text).

Important: `docs/schema/*` is reserved for generated schema reference pages.
For content organization decisions, see
[Documentation Writing Guide](documentation_writing_guide.md).

## 1) Generated Schema Navigation

Run:

```bash
uv run python scripts/generate_docs_pipeline.py
```

What it does:

1. cleans previously generated schema docs,
2. regenerates diagrams and schema pages from introspection,
3. updates schema navigation structure in docs config,
4. validates generated output.

Output stability:
- for the same schema revision and script version, generated content is stable
  because class discovery and rendered lists are sorted;
- updates should appear only when schema/docs sources change.

Primary script inputs:

- `scripts/verticals.py` (domain/page grouping),
- `scripts/gen_docs.py`, `scripts/gen_diagrams.py` (page + diagram generation),
- `scripts/meta_introspect.py` (schema introspection).

For implementation details of pipeline steps, filtering, and vertical design
rules, see `scripts/README.md` in the repository.

### Deterministic Navigation Ordering

Schema navigation ordering is generated automatically and deterministically:

- top-level domain order is fixed to:
  `simulation`, `model_system`, `model_method`, `outputs`, `workflow`;
- for each domain, the domain root page is always first;
- remaining child pages are sorted alphabetically by display title;
- optional override: set `nav_order` in a vertical spec in `scripts/verticals.py`
  to force explicit ordering for exceptional cases (lower value sorts first).

This ordering is applied to both:
- `mkdocs.yml` (`Schema Navigation` block),
- `docs/schema/.pages`.

### Auto-discovered Backlinks to Explanation Pages

Generated schema pages include a `Related Pages` section populated
automatically from links already present in `docs/explanation/**/*.md`.

Convention:

- if an explanation page links to `schema/<vertical>.md`, that explanation page
  is listed back on the corresponding generated schema page;
- links are discovered by parsing markdown and resolving relative paths;
- when no backlinks are found, no backlink section content is rendered.

For reliable results (including agent-authored docs), always include canonical
links to relevant `schema/*.md` pages from explanation pages.
This is especially important for workflow explanation pages because the
workflow vertical family is fully generated in `docs/schema/`.

### Guidelines for Adding Auto-doc Navigation

Add a dedicated auto-doc section when:

- The scope is medium/large (roughly 3+ generated pages or a full schema
  subdomain with inheritance/relations).
- The content is schema-structural and expected to evolve through
  introspection/generation (not hand-maintained prose).

Implementation guidelines:

- Do not manually edit navigation in `mkdocs.yml`.
- Navigation is generated automatically through `scripts/verticals.py` and the
  docs pipeline.
- Top-level section ordering is consistent with schema structure.
- Child pages follow root-first ordering, then deterministic sorting
  (alphabetical by title unless overridden via `nav_order` in vertical spec).

## 2) Generated Explanation Fragments

Run:

```bash
uv run python scripts/generate_explanation_fragments.py
```

This writes stable Markdown fragments to:

- `docs/snippets/generated/model_method_hierarchy.md`
- `docs/snippets/generated/model_method_family_map.md`

These fragments are included in hand-written pages via snippet includes and
reduce manual duplication.

## 3) Snippet Protocol (Executable Docs)

Canonical snippet authoring conventions are documented in
[Documentation Writing Guide](documentation_writing_guide.md#5-keep-examples-executable).

Run snippet validation and execution via:

```bash
uv run python -m pytest -q tests/test_doc_snippets.py
```

This test module validates snippet references, syntax, and execution behavior
for runnable examples discovered via `# docs-snippet: runnable`.

## 4) Ownership and Update Rules

Regenerate documentation when:

- **Schema structure changes** → run `generate_docs_pipeline.py`
  - Affects `docs/schema/*` pages and navigation
  - Required before opening PR with schema changes
- **Explanation inventory changes** → run `generate_explanation_fragments.py`
  - Affects `docs/snippets/generated/*.md`
- **Code examples change** → update snippet files and tests together
  - Affects `docs/snippets/*` and `tests/test_doc_snippets.py`

Commit policy:

- Keep generated outputs deterministic and committed with the corresponding
  source-script changes.
- Generated files should only change when their source schema/script changes.

## 5) CI Docs Integrity Gate

GitHub Actions includes a `docs-integrity` job in
`.github/workflows/actions.yml` that runs:

1. `scripts/gen_docs.py` and `scripts/generate_explanation_fragments.py`,
2. a diff check on generated artifacts (`docs/schema`, `docs/snippets/generated`),
3. `tests/test_doc_snippets.py`,
4. `mkdocs build -q`.

Use these same commands locally before opening PRs that touch documentation
automation, snippets, or generated docs.
