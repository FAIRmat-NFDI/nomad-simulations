# Diagram Simplification - Backup & Restoration Guide

## Summary of Changes

The mermaid classDiagram visualizations have been simplified to remove:

1. **Redundant edge labels** - Labels that match the target class name are removed
2. **UML divider lines** - Horizontal lines separating class sections
3. **Empty attribute/method sections** - The empty boxes below class names

## Files Modified

### 1. `scripts/gen_diagrams.py`
- **Backup:** `scripts/gen_diagrams.py.backup`
- **Changes:**
  - Added `normalize_label()` function to filter redundant labels
  - Changed class format to `class {ClassName} { }` (empty braces)
  - Added documentation header explaining restoration

### 2. `scripts/mermaid_to_svg_simple.py`
- **Changes:**
  - Added `clean_svg_dividers()` function to post-process SVG
  - Removes `<g class="divider">`, `<g class="members-group">`, `<g class="methods-group">` elements
  - Added documentation explaining how to disable cleaning

## Restoration Guide

### To restore redundant labels:

In `scripts/gen_diagrams.py`, modify the `normalize_label()` function:

```python
# CURRENT (simplified):
def normalize_label(label: str, target: str) -> str:
    label_normalized = label.replace('_', '').lower()
    target_normalized = target.lower()
    if label_normalized == target_normalized:
        return ''  # Remove redundant label
    if label_normalized == target_normalized + 's':
        return ''  # Remove plural form
    return label

# TO RESTORE (show all labels):
def normalize_label(label: str, target: str) -> str:
    return label  # Keep all labels
```

### To restore UML-style boxes with dividers:

In `scripts/mermaid_to_svg_simple.py`, comment out the cleaning step:

```python
# CURRENT (simplified):
if result.returncode == 0 and output_path.exists():
    svg_content = output_path.read_text()
    svg_content = clean_svg_dividers(svg_content)  # ← Comment this line
    if not svg_content.startswith('<?xml'):
        svg_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_content
    output_path.write_text(svg_content)
    return True

# TO RESTORE UML boxes:
if result.returncode == 0 and output_path.exists():
    svg_content = output_path.read_text()
    # svg_content = clean_svg_dividers(svg_content)  # ← Commented out
    if not svg_content.startswith('<?xml'):
        svg_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_content
    output_path.write_text(svg_content)
    return True
```

### To restore full UML-style classes with attributes/methods:

In `scripts/gen_diagrams.py`, change class definitions:

```python
# CURRENT (simplified):
lines.append(f'    class {node} {{')
lines.append(f'    }}')

# TO RESTORE UML with attributes/methods:
lines.append(f'    class {node} {{')
lines.append(f'        +attribute_name : Type')
lines.append(f'        +method_name()')
lines.append(f'    }}')
```

## After Restoration

After making any changes, regenerate the diagrams:

```bash
cd /path/to/nomad-simulations
.pyenv/bin/python scripts/gen_diagrams.py
rm -f docs/assets/diagrams/*.svg
.pyenv/bin/python scripts/mermaid_to_svg_simple.py
.pyenv/bin/python -m mkdocs build
```

## Visual Comparison

**Before (UML-style):**
```
┌─────────────────┐
│ ModelMethod     │
├─────────────────┤  ← divider
│                 │  ← empty attributes
├─────────────────┤  ← divider  
│                 │  ← empty methods
└─────────────────┘
     ↓ numerical_settings (redundant label)
┌─────────────────┐
│ NumericalSettings│
└─────────────────┘
```

**After (simplified):**
```
┌─────────────────┐
│ ModelMethod     │
└─────────────────┘
     ↓ (no label - redundant)
┌─────────────────┐
│ NumericalSettings│
└─────────────────┘
```

## Labels Kept vs Removed

**Removed (redundant):**
- `BaseModelMethod --> NumericalSettings` (label "numerical_settings" removed)
- `BaseSimulation --> Program` (label "program" removed)
- `DFT --> XCFunctional` (label "xc_functionals" removed - plural)

**Kept (non-redundant):**
- `ModelMethod --> BaseModelMethod : contributions` (label kept - different from target)
