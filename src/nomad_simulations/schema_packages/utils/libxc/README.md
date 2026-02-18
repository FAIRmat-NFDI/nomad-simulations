# LibXC Normalization and Registry Provenance

This folder contains the utilities used to:

- map free-form XC strings to LibXC labels
- build XC components in `model_method.py`
- look up functional metadata from a local registry
- document how `xc_registry_min.json` was generated

## Scope

- `expand.py`
- `build.py`
- `registry.py`
- `model_method.py` (`XCFunctional.normalize`, `DFT.normalize`)
- `xc_registry_min.json`

---

## XC String Normalization

Input field: `XCFunctional.functional_key` (free-form text such as `PBE`,
`B3LYP`, `SCAN+rVV10`, `ωB97X-V`).

### 1. Tokenization and token cleanup (`expand.py`)

Split regex: `[+/,\s]+`

Each token is normalized by:

- converting to uppercase
- replacing omega symbols (`ω`, `Ω`, `Ω`) with `W`
- removing parenthesized text `(...)`
- removing separators: whitespace, `+`, `/`, `,`, `_`, `-`

### 2. Token to LibXC label resolution

For each normalized token, `_labels_for_token` checks in this order:

1. direct `XC_` label match in registry
2. `HYB` aliases from `aliases.json`
3. `BASE` aliases from `aliases.json`
4. hard-coded synonym helpers:
   - `LCWPBE` / `LCOMEGAPBE` -> alias `LC-ωPBE`
   - `SOGGA11X` -> `XC_GGA_X_SOGGA11`
5. rung fallback:
   - choose rung with `RUNG_HINT[token]`
   - select first present label from `FALLBACK_BY_RUNG[rung]`

All candidates are filtered against `xc_registry_min.json`.

### 3. Merge behavior

`expand_to_libxc_labels(raw)` returns `sorted(set(labels))` across all tokens.

Unknown tokens are ignored.

---

## Component Construction in `model_method.py`

### `XCFunctional.normalize`

If `xc.components` is empty and `functional_key` is set:

- call `expand_to_libxc_labels(functional_key)`
- convert each label with `spec_from_label`
- append `XCComponent` entries with `weight=1.0`

Expansion errors are caught and logged as warnings.

### `global_exact_exchange`

`xc.global_exact_exchange` is inferred from
`components[*].fraction_exact_exchange`:

- one value -> use it
- multiple identical values -> use that value
- mixed values -> keep `None`

Alias names are not used for this inference.

---

## Jacob's Ladder Assignment in `DFT.normalize`

After `XCFunctional.normalize`, `jacobs_ladder` is set from:

1. derived family from components (ranked):
   `LDA < GGA < meta-GGA < hybrid-GGA < hybrid-meta-GGA`
2. hinted family from `infer_rung_hint(functional_key)` via `RUNG_HINT`

Assignment rule:

- if both exist, use the higher-ranked one
- if only hint exists, use hint
- if only derived exists, use derived
- otherwise keep existing value or use `'unavailable'`

So `RUNG_HINT` can override the component-derived value when it has higher
rank.

---

## Registry API

`registry.py` exposes:

- `lookup_by_label(label)`
- `lookup_by_id(id)`

`lookup_by_label` supports relaxed, separator-insensitive key matching.

---

## Known Limitations

- `/` is a token separator, so an alias like `PBE0-1/3` is split before alias
  lookup.
- Separator removal includes `_`, so raw LibXC text is less likely to match
  the direct `XC_` branch.
- Expansion is alias-table driven; unknown and non-aliased tokens are ignored.

---

## Provenance of `xc_registry_min.json`

This section records how `xc_registry_min.json` is generated from LibXC source.

Validated with LibXC `7.0.0`.

### Inputs

- `scripts/get_functional_info.py`
- `src/*.c`
- `libxc_docs.json` (intermediate file)

### Outputs

- `libxc_docs.json`
- `xc_registry_min.json`
- `xc_registry.py` (companion `REGISTRY` dict)

### Reproducible Steps (run from LibXC repo root)

1. Generate `libxc_docs.json`:

```bash
python3 scripts/get_functional_info.py --srcdir=src
```

2. Verify that it is populated:

```bash
test -s libxc_docs.json
rg -c '"number"' libxc_docs.json
```

Expected: non-zero count. For the LibXC `7.0.0` run used here, the count was
`679`.

3. Convert to NOMAD registry files:

```bash
python3 - <<'PY'
import json, pathlib, re

ROOT = pathlib.Path(".")
DOCS = ROOT / "libxc_docs.json"

RE_INFO = re.compile(r"xc_func_info_([a-z0-9_]+)\s*=\s*{", re.I)
RE_ALPHA = re.compile(r"\bcam_alpha\s*=\s*([0-9eE.+-]+)")
RE_OMEGA = re.compile(r"\bcam_omega\s*=\s*([0-9eE.+-]+)")

def keyize_label(xc_label: str) -> str:
    return (
        xc_label.replace("XC_", "")
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
        .upper()
    )

def label_from_codename(codename: str) -> str:
    return "XC_" + codename.upper()

def norm_family(libxc_family: str, label: str) -> str:
    if label.startswith("LDA_"):
        return "LDA"
    if label.startswith("GGA_"):
        return "GGA"
    if label.startswith("MGGA_"):
        return "meta-GGA"
    if label.startswith("HYB_GGA_"):
        return "hybrid-GGA"
    if label.startswith("HYB_MGGA_"):
        return "hybrid-meta-GGA"
    f = libxc_family.replace("XC_FAMILY_", "").lower()
    return {
        "lda": "LDA",
        "gga": "GGA",
        "mgga": "meta-GGA",
        "hyb_gga": "hybrid-GGA",
        "hyb_mgga": "hybrid-meta-GGA",
    }.get(f, "GGA")

def norm_kind(libxc_kind: str, label: str) -> str:
    if "_X_" in label:
        return "exchange"
    if "_C_" in label:
        return "correlation"
    if "_XC_" in label:
        return "xc"
    if "_K_" in label:
        return "k"

    k = libxc_kind.replace("XC_", "").lower()
    if "exchange_correlation" in k:
        return "xc"
    if "exchange" in k and "correlation" not in k:
        return "exchange"
    if "correlation" in k and "exchange" not in k:
        return "correlation"
    if "kinetic" in k:
        return "k"
    return "xc"

def scan_alpha_omega():
    out = {}
    for path in (ROOT / "src").rglob("*.c"):
        try:
            txt = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        m = RE_INFO.search(txt)
        if not m:
            continue

        label = "XC_" + m.group(1).upper()
        a = RE_ALPHA.search(txt)
        w = RE_OMEGA.search(txt)
        if a or w:
            out[label] = {
                "alpha": float(a.group(1)) if a else None,
                "omega": float(w.group(1)) if w else None,
            }
    return out

def main():
    data = json.loads(DOCS.read_text(encoding="utf-8"))
    items = []
    for codename, info in data.items():
        label = label_from_codename(codename)
        items.append(
            {
                "id": info["number"],
                "label": label,
                "name": info["description"],
                "family": norm_family(info.get("family", ""), label),
                "kind": norm_kind(info.get("kind", ""), label),
                "alpha": None,
                "omega": None,
            }
        )

    items.sort(key=lambda x: x["id"])

    alpha_omega = scan_alpha_omega()
    for item in items:
        if item["label"] in alpha_omega:
            item["alpha"] = alpha_omega[item["label"]]["alpha"]
            item["omega"] = alpha_omega[item["label"]]["omega"]

    (ROOT / "xc_registry_min.json").write_text(
        json.dumps(items, indent=2), encoding="utf-8"
    )

    lines = ["# Auto-generated from libxc_docs.json", "REGISTRY = {"]
    for item in items:
        lines.append(
            "  '{key}': {{'id': {id}, 'label': '{label}', 'family': '{family}', "
            "'kind': '{kind}', 'name': {name}, 'alpha': {alpha}, 'omega': {omega}}},".format(
                key=keyize_label(item["label"]),
                id=item["id"],
                label=item["label"],
                family=item["family"],
                kind=item["kind"],
                name=repr(item["name"]),
                alpha=repr(item["alpha"]),
                omega=repr(item["omega"]),
            )
        )
    lines.append("}")
    (ROOT / "xc_registry.py").write_text("\n".join(lines), encoding="utf-8")

    print(f"OK: wrote xc_registry.py and xc_registry_min.json with {len(items)} entries.")

main()
PY
```

4. Validate output files:

```bash
test -s xc_registry_min.json
test -s xc_registry.py
rg -c '"id"' xc_registry_min.json
sed -n '1,20p' xc_registry_min.json
```

### Deterministic conversion rules

- each source key (for example `gga_x_pbe`) becomes `XC_GGA_X_PBE`
- `id` comes from `info["number"]`
- `name` comes from `info["description"]`
- `family` is derived from label prefix first, then `info["family"]`, fallback
  `GGA`
- `kind` is derived from label token first, then `info["kind"]`, fallback `xc`
- entries are sorted by ascending `id`
- `alpha`/`omega` are filled by scanning `src/**/*.c` for
  `cam_alpha`/`cam_omega` in matching `xc_func_info_*` blocks
- `xc_registry.py` keys are compacted labels
  (`XC_GGA_X_PBE` -> `GGAXPBE`)

### Common failure mode

If step 1 is run without `--srcdir=src`, LibXC may scan the wrong path and
produce:

```json
{}
```

in `libxc_docs.json`.

### Output record schema (`xc_registry_min.json`)

```json
{
  "id": 101,
  "label": "XC_GGA_X_PBE",
  "name": "Perdew, Burke & Ernzerhof exchange",
  "family": "GGA",
  "kind": "exchange",
  "alpha": null,
  "omega": null
}
```

`alpha` and `omega` are numeric when found in source; otherwise `null`.

For `nomad-simulations`, copy the generated `xc_registry_min.json` into this
directory and commit it.
