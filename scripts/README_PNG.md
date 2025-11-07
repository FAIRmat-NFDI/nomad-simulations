# Mermaid to PNG Conversion

## Overview

This directory contains scripts to convert Mermaid diagrams to PNG images for better zoom functionality in the documentation.

## Prerequisites

You need Node.js/npm installed. The scripts use `npx` to run `@mermaid-js/mermaid-cli`.

Check if you have it:
```bash
which npx
```

If not, install Node.js from https://nodejs.org/

## Usage

### Option 1: Manual Conversion (After generating docs)

1. Generate documentation normally:
   ```bash
   python scripts/gen_docs.py
   ```

2. Convert Mermaid to PNG:
   ```bash
   python scripts/mermaid_to_png.py
   ```

This will:
- Scan `docs/schema/*.md` for Mermaid code blocks
- Convert each to PNG in `docs/assets/diagrams/`
- Replace Mermaid code blocks with click-zoom image references

### Option 2: Automated Workflow

Run the combined script:
```bash
python scripts/gen_docs_with_png.py
```

This runs both steps automatically.

## How It Works

1. **Extract**: The script finds all ` ```mermaid ` code blocks in your markdown files
2. **Convert**: Uses `@mermaid-js/mermaid-cli` (via npx) to render PNG images at high resolution
3. **Replace**: Updates markdown to use the PNG with click-zoom wrapper:
   ```html
   <div class="click-zoom">
       <label>
           <input type="checkbox">
           <img src="../assets/diagrams/methods_0.png" alt="methods_0 diagram" width="80%">
       </label>
   </div>
   ```

## Configuration

### Conversion Options

The PNG conversion uses these settings (in `mermaid_to_png.py`):
- `-b transparent`: Transparent background
- `-w 2000`: Width of 2000px for high resolution
- `-s 2`: Scale factor for better quality

You can adjust these in the script if needed.

### Custom Paths

Both scripts accept command-line arguments:

```bash
python scripts/mermaid_to_png.py --docs-dir docs/custom --assets-dir docs/images
```

## Styling

The click-zoom functionality uses CSS defined in `docs/stylesheets/mermaid-zoom.css`:

```css
.click-zoom input[type=checkbox] {
    display: none;
}

.click-zoom img {
    transition: transform 0.25s ease;
    cursor: zoom-in;
}

.click-zoom input[type=checkbox]:checked ~ img {
    transform: scale(2);
    cursor: zoom-out;
}
```

Users click the image to zoom in (2x), click again to zoom out.

## Troubleshooting

### "npx command not found"
Install Node.js from https://nodejs.org/

### Timeout errors
The conversion timeout is set to 30 seconds per diagram. For very large diagrams, increase the timeout in `mermaid_to_png.py`:

```python
timeout=60  # Increase from 30 to 60 seconds
```

### Images not showing
Check that:
1. PNG files exist in `docs/assets/diagrams/`
2. Relative paths in markdown are correct
3. mkdocs.yml includes the assets directory

## Reverting to Mermaid

To go back to inline Mermaid diagrams:
1. Run `python scripts/gen_docs.py` (regenerates with Mermaid)
2. Don't run the PNG conversion

The original Mermaid code is preserved in `scripts/gen_diagrams.py` and templates.
