# Documentation Writing Guide

Use this as a short checklist when updating docs.

## 1) Keep Responsibilities Clear

- `Schema Navigation` (generated): structure, quantities, relationships.
- `Schema Explanation` (hand-written): rationale, invariants, usage guidance.
- Do not duplicate generated reference content in explanation pages.
- Add canonical links to relevant `schema/*.md` pages so generated schema docs
  can auto-link back to explanations.

## 2) Keep Pages Focused

- One page, one concern.
- If text repeats across pages, extract it and link.
- Prefer short sections with explicit headings.

## 3) Use a Simple Page Pattern

1. Purpose
2. Link to generated page(s)
3. Rules/invariants
4. Usage guidance (parser/normalization)
5. Pitfalls and related links

## 4) Keep Examples Executable

- Store snippets in `docs/snippets/`.
- Include snippets via `--8<-- "snippets/<path>/<file>.py"`.
- Ensure every snippet has test coverage in `tests/test_doc_snippets.py`.

## 5) Assets and Paths

- Store page-specific images in a local `images/` folder.
- Reference with `./images/<file>` whenever possible.

## 6) Before Opening a PR

- Run the docs generation pipeline if schema structure changed.
- Update only affected explanation pages.
- Check `mkdocs.yml` navigation paths/titles.
- Verify links and docs build.
