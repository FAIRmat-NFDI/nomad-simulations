# Documentation Automation Guide

This page centralizes the automation workflows used to generate and validate
documentation in `nomad-simulations`.

## Scope

Automation is split into two tracks:

- generated schema reference pages (`docs/schema/*`),
- reusable fragments/snippets used by hand-written explanation pages.

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

Primary script inputs:

- `scripts/verticals.py` (domain/page grouping),
- `scripts/gen_docs.py`, `scripts/gen_diagrams.py` (page + diagram generation),
- `scripts/meta_introspect.py` (schema introspection).

## 2) Generated Explanation Fragments

Run:

```bash
uv run python scripts/generate_explanation_fragments.py
```

This writes deterministic Markdown fragments to:

- `docs/snippets/generated/model_method_hierarchy.md`
- `docs/snippets/generated/model_method_family_map.md`

These fragments are included in hand-written pages via snippet includes and
reduce manual duplication.

## 3) Snippet Protocol (Executable Docs)

For code examples in explanation pages:

1. store code in `docs/snippets/...`,
2. include in Markdown via `--8<-- "snippets/<path>/<file>.py"`,
3. ensure test coverage in `tests/test_doc_snippets.py`.

Coverage checks include:

- referenced snippet path existence,
- Python syntax validation,
- explicit execution for runnable examples,
- coverage guard to prevent untested snippets.

## 4) Validation Commands

Use these gates before opening docs PRs:

```bash
uvx ruff@0.15.1 check --fix .
uv run ruff format --check .
.venv/bin/python -m pytest -q tests/test_doc_snippets.py
.venv/bin/mkdocs build -q
```

Optional full test run:

```bash
.venv/bin/python -m pytest -q
```

## 5) Ownership and Update Rules

- If schema structure changes, regenerate schema docs.
- If explanation inventory text changes, regenerate explanation fragments.
- If examples change, update snippets and snippet tests in the same PR.
- Keep generated outputs deterministic and committed with the corresponding
  source-script changes.
