# LibXC XC Canonicalization

Scope:

- `expand.py`
- `build.py`
- `registry.py`
- `model_method.py` (`XCFunctional.normalize`, `DFT.normalize`)

---

## Input

`XCFunctional.functional_key` is parsed as a free-form XC string, for example:
`PBE`, `B3LYP`, `SCAN+rVV10`, `ωB97X-V`.

---

## Expansion pipeline

### 1) Tokenization and normalization (`expand.py`)

- Token split regex: `[+/,\s]+`
- Per token:
  - uppercase
  - normalize omega (`ω`, `Ω`, `Ω` -> `W`)
  - drop parenthesized text `(...)`
  - remove separators: whitespace, `+`, `/`, `,`, `_`, `-`

### 2) Token-to-label resolution order

For each normalized token, `_labels_for_token` checks:

1. `XC_` label branch: return label if present in registry
2. `HYB` aliases from `aliases.json`
3. `BASE` aliases from `aliases.json`
4. synonym helpers:
   - `LCWPBE` / `LCOMEGAPBE` -> alias `LC-ωPBE`
   - `SOGGA11X` -> `XC_GGA_X_SOGGA11`
5. rung fallback:
   - `RUNG_HINT[token]` chooses rung
   - first existing option in `FALLBACK_BY_RUNG[rung]`

All candidate labels are filtered against `xc_registry_min.json`.

### 3) Merge

`expand_to_libxc_labels(raw)` returns `sorted(set(labels))` across all tokens.

Unknown tokens are ignored.

---

## Component construction

In `XCFunctional.normalize` (`model_method.py`):

- If `xc.components` is empty and `functional_key` is set:
  - expand using `expand_to_libxc_labels`
  - build specs via `spec_from_label`
  - append `XCComponent` with `weight=1.0`
- Expansion exceptions are caught and logged as warnings.

### Global exact exchange

`xc.global_exact_exchange` is inferred from `fraction_exact_exchange` in
components:

- one value -> use it
- multiple identical values -> use that value
- otherwise -> keep `None`

Alias names are not used to infer exact exchange.

---

## Jacob's ladder assignment (`DFT.normalize`)

After `XCFunctional.normalize`:

1. derive family from components using rank:
   `LDA < GGA < meta-GGA < hybrid-GGA < hybrid-meta-GGA`
2. derive hint family from `infer_rung_hint(functional_key)` using `RUNG_HINT`
3. set `jacobs_ladder`:
   - higher-ranked value if both derived and hinted are present
   - hinted value if only hint exists
   - derived value if only derived exists
   - otherwise existing value or `'unavailable'`

`RUNG_HINT` can override component-derived family when its rank is higher.

---

## Registry API

`registry.py` provides:

- `lookup_by_label(label)`
- `lookup_by_id(id)`

`lookup_by_label` supports relaxed key matching via separator-insensitive
keyization.

---

## Limitations

- `/` is a token separator, so aliases containing `/` in a single name (for
  example `PBE0-1/3`) are split before alias lookup.
- Normalization removes separators, including `_`. For raw LibXC text input,
  this makes the `XC_` branch uncommon.
- Expansion is alias-table driven; non-aliased unknown tokens are ignored.
