# Documentation Automation Guide

The docs automation has two responsibilities:
- generate reference pages from schema introspection (`docs/schema/*`),
- generate reusable fragments consumed by hand-written explanation pages.

These are script-driven outputs (not AI-generated text).

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

Canonical snippet authoring rules live in
[Documentation Writing Guide](documentation_writing_guide.md).
Marker and folder conventions are documented in `docs/snippets/README.md`.

Run snippet validation and execution via:

```bash
uv run python -m pytest -q tests/test_doc_snippets.py
```

This test module validates snippet references, syntax, and execution behavior
for runnable examples discovered via `# docs-snippet: runnable`.

## 4) Ownership and Update Rules

- If schema structure changes, regenerate schema docs.
- If explanation inventory text changes, regenerate explanation fragments.
- If examples change, update snippets and snippet tests in the same PR.
- Keep generated outputs deterministic and committed with the corresponding
  source-script changes.
