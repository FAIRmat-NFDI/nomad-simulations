#!/usr/bin/env python3
"""
Convert Mermaid diagrams to SVG with simple click-zoom.

This script:
1. Finds PNG references in markdown files
2. Reads the mermaid source from .png.mmd files
3. Converts them to SVG using mermaid-cli
4. Updates markdown to reference SVG instead of PNG
5. Adds XML declaration for proper browser rendering

The SVG files work with the existing click-zoom JavaScript/CSS.
"""

import re
import subprocess
import sys
from pathlib import Path


def extract_png_references(md_file: Path):
    """Extract PNG image references from markdown."""
    content = md_file.read_text()
    
    # Pattern: ![title diagram](path.png){...}
    pattern = r'!\[([^]]+) diagram\]\(\.\./assets/diagrams/([^)]+)\.png\)\{[^}]+\}'
    
    matches = re.findall(pattern, content)
    return [(title, filename) for title, filename in matches]


def convert_mermaid_to_svg(mermaid_code: str, output_path: Path) -> bool:
    """Convert Mermaid code to SVG using mermaid-cli."""
    
    # Create a temporary mermaid file
    temp_mmd = output_path.with_suffix('.svg.mmd')
    
    try:
        # Write mermaid code to temp file
        temp_mmd.write_text(mermaid_code)
        
        # Run mermaid CLI to generate SVG
        result = subprocess.run(
            ['npx', '-y', '@mermaid-js/mermaid-cli', '-i', str(temp_mmd), '-o', str(output_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Clean up temp file
        if temp_mmd.exists():
            temp_mmd.unlink()
        
        if result.returncode == 0 and output_path.exists():
            # Add XML declaration if missing
            svg_content = output_path.read_text()
            if not svg_content.startswith('<?xml'):
                svg_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_content
                output_path.write_text(svg_content)
            return True
        else:
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("Error: Conversion timed out")
        if temp_mmd.exists():
            temp_mmd.unlink()
        return False
    except Exception as e:
        print(f"Error: {e}")
        if temp_mmd.exists():
            temp_mmd.unlink()
        return False


def update_markdown_png_to_svg(md_file: Path):
    """Replace PNG references with SVG references in markdown."""
    content = md_file.read_text()
    
    # Pattern: .png in image references
    pattern = r'(!\[[^]]+\]\(\.\./assets/diagrams/[^)]+)\.png(\)\{[^}]+\})'
    
    # Replace .png with .svg
    new_content = re.sub(pattern, r'\1.svg\2', content)
    
    if new_content != content:
        md_file.write_text(new_content)
        return True
    
    return False


def process_docs(docs_dir: Path = Path('docs/schema'), assets_dir: Path = Path('docs/assets/diagrams')):
    """Process all markdown files and convert PNG references to SVG."""
    
    # Create assets directory if it doesn't exist
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all markdown files
    md_files = list(docs_dir.glob('*.md'))
    
    total_converted = 0
    total_updated = 0
    
    for md_file in md_files:
        print(f"Processing {md_file.name}...")
        
        # Extract PNG references
        png_refs = extract_png_references(md_file)
        
        if not png_refs:
            print("  No PNG diagram references found")
            continue
        
        for title, filename in png_refs:
            # Look for the .png.mmd file created by mermaid_to_png.py
            mmd_file = assets_dir / f"{filename}.png.mmd"
            
            if not mmd_file.exists():
                print(f"  ⚠ Warning: {mmd_file.name} not found, skipping {title}")
                continue
            
            # Read mermaid code
            mermaid_code = mmd_file.read_text()
            
            # Generate SVG filename
            svg_filename = f"{filename}.svg"
            svg_path = assets_dir / svg_filename
            
            print(f"  Converting {title} to SVG...")
            
            # Convert to SVG
            if convert_mermaid_to_svg(mermaid_code, svg_path):
                print(f"  ✓ Generated {svg_filename}")
                total_converted += 1
            else:
                print(f"  ✗ Failed to convert {title}")
        
        # Update markdown to use SVG instead of PNG
        if update_markdown_png_to_svg(md_file):
            print(f"  ✓ Updated markdown to use SVG")
            total_updated += 1
    
    print(f"\nTotal diagrams converted to SVG: {total_converted}")
    print(f"Total markdown files updated: {total_updated}")
    return total_converted


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert PNG diagram references to SVG with click-zoom')
    parser.add_argument('--docs-dir', type=Path, default=Path('docs/schema'),
                        help='Directory containing markdown files')
    parser.add_argument('--assets-dir', type=Path, default=Path('docs/assets/diagrams'),
                        help='Directory containing diagram files')
    
    args = parser.parse_args()
    
    try:
        process_docs(args.docs_dir, args.assets_dir)
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(1)
