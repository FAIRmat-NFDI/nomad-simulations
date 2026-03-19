# Documentation Snippets

This folder contains source files used by markdown docs via snippet includes.

## Snippet Types

- `illustrative`: partial examples used for explanation; must stay syntactically
  valid and be referenced from docs pages or covered by dedicated tests.
- `runnable`: standalone examples that should execute without extra fixtures.
  Mark these files with:
  - `# docs-snippet: runnable`

Optional marker:
- `# docs-snippet: skip-coverage`
  - use only for exceptional cases and document the reason in the PR.

## Testing Contract

`tests/test_doc_snippets.py` enforces:

- referenced snippet paths exist,
- syntax validity for all Python snippets,
- execution of runnable snippets (marker-based discovery),
- coverage guard so every snippet is either:
  - referenced in markdown,
  - directly tested, or
  - explicitly marked to skip coverage.
