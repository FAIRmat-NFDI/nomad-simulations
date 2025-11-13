# LibXC Functional Canonicalization

This module converts **code-specific exchange–correlation (XC) labels** into a **canonical, LibXC-grounded representation**.  
It accepts aliases such as `PBE`, hybrids like `B3LYP`, or composite forms like `SCAN+rVV10`, and produces normalized **LibXC components** (`XCComponent` instances) with consistent metadata (`family`, `kind`, `id`, etc.).

---

## Aim

1. **Unify XC naming** across electronic-structure codes by resolving them to LibXC identifiers.  
2. **Make functional components explicit** — making functional components explicit as far as LibXC exposes them.  
3. **Preserve hybrid parameters** when available (`α`, `ω`, SR/LR fractions).  
4. **Provide a single canonical label** (`functional_key`) for user-facing filtering, while keeping full LibXC detail internally.

> **Background:**  
> [LibXC](https://libxc.gitlab.io/) is the reference library defining the mathematical kernels for all standard density functionals (LDA, GGA, meta-GGA, hybrids).  
> It distinguishes each kernel by a stable name like `XC_GGA_X_PBE` and a numeric ID.  
> This canonicalization follows the same separation principle: each kernel is treated as one building block.

---

## Input Forms Accepted

- **Human-readable aliases:** `LDA`, `PBE`, `PW91`, `TPSS`, `SCAN`, `r2SCAN`, `B3LYP`, etc.  
- **Hybrid or range-separated forms:** `PBE0`, `HSE06`, `LC-ωPBE`, `CAM-B3LYP`, etc.  
- **Raw LibXC labels:** `XC_GGA_X_PBE`, `XC_GGA_C_PBE`, `XC_HYB_GGA_XC_B3LYP`, etc.  

The module is code-agnostic — any parser providing a string can normalize it through this interface.

---

## Canonicalization Pipeline

### 1. Tokenization & Normalization
- Input strings are uppercased, `ω` is normalized to `W`, all text in parentheses is dropped, and separators (`space`, `+`, `/`, `_`, `-`, `,`) are removed. Tokenization splits on `[+/,\s]+`.
- Known suffixes like `-D3` or `+VV10` are recognized but **not yet parsed into separate dispersion or nonlocal correlation models** — they remain part of the functional key.

### 2. Alias Expansion → LibXC Components
Aliases are expanded using a curated lookup table (`expand.py`):

| Input Alias | Expanded Components |
|--------------|---------------------|
| `PBE` | `XC_GGA_X_PBE`, `XC_GGA_C_PBE` |
| `SVWN` | `XC_LDA_X`, `XC_LDA_C_VWN` |
| `TPSS` | `XC_MGGA_X_TPSS`, `XC_MGGA_C_TPSS` |

This ensures consistent resolution against LibXC definitions.

### 3. Registry Lookup (`registry.py`)
Each expanded label is matched against a lightweight internal registry (`xc_registry_min.json`)  
to populate standard LibXC metadata:

- **`family`** → `LDA`, `GGA`, `meta-GGA`, `hybrid-GGA`, `hybrid-meta-GGA`  
- **`kind`** → `exchange`, `correlation`, or `xc`  
- **`libxc_id`** → stable LibXC numeric identifier  
- **`display_name`** → human-readable name (e.g., “Perdew, Burke & Ernzerhof”)

### 4. Component Construction (`build.py`)
Each resolved label becomes an `XCComponent`, carrying:
- canonical label (`XC_GGA_X_PBE`)  
- LibXC ID and family/kind metadata  
- optional hybrid parameters (`fraction_exact_exchange`, `range_separation_parameter`)  
- numerical `weight` (default 1.0)

### 5. Attachment to DFT Section
During `DFT.normalize()`:
- If `xc.components` is empty but a `functional_key` is provided,  
  it is expanded into canonical LibXC components and attached.  
- The **highest Jacob’s ladder family** among components sets `jacobs_ladder`.  
- If a unique hybrid fraction (`α`) is found, it is propagated to `exact_exchange_mixing_factor`.

---

## Canonical Functional Key (`functional_key`)

While LibXC defines each **exchange**, **correlation**, and **hybrid** kernel separately  
(e.g., `XC_GGA_X_PBE`, `XC_GGA_C_PBE`), users typically refer to these collectively using one name — e.g., “PBE”.

This canonicalization introduces:

- **`functional_key`** → one user-facing alias representing the entire functional  
  *(e.g., `PBE`, `PBE0`, `B3LYP`, `SCAN+rVV10`)*  
- **`components`** → explicit LibXC-resolved kernels underneath  
  *(e.g., `["XC_GGA_X_PBE", "XC_GGA_C_PBE"]`)*

Example:
```text
PBE    → functional_key = "PBE"
          components = ["XC_GGA_X_PBE", "XC_GGA_C_PBE"]

B3LYP  → functional_key = "B3LYP"
          components = ["XC_HYB_GGA_XC_B3LYP"]


