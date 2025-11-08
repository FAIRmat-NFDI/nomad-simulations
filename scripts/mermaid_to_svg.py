#!/usr/bin/env python3
"""
Convert Mermaid diagrams in markdown files to SVG images.

This script:
1. Scans markdown files for Mermaid code blocks
2. Converts them to high-quality SVG using @mermaid-js/mermaid-cli
3. Replaces the Mermaid code blocks with interactive SVG viewers

Usage:
    python scripts/mermaid_to_svg.py
    python scripts/mermaid_to_svg.py --docs-dir docs/schema --assets-dir docs/assets/diagrams

Requirements:
    - Node.js/npm with npx
    - @mermaid-js/mermaid-cli (installed via npx)
"""

import re
import subprocess
import sys
from pathlib import Path


def extract_mermaid_blocks(md_file: Path) -> list[tuple[str, str]]:
    """Extract Mermaid code from PNG temp files (created by mermaid_to_png.py)."""
    content = md_file.read_text()
    
    # Look for PNG diagram references
    png_pattern = r'!\[([^\]]+)_(\d+) diagram\]\(\.\./assets/diagrams/[^\)]+\.png\)'
    matches = re.findall(png_pattern, content)
    
    if not matches:
        return []
    
    # Read mermaid code from temp files created by mermaid_to_png
    assets_dir = md_file.parent.parent / 'assets' / 'diagrams'
    results = []
    
    for base_name, index in matches:
        title = f"{base_name}_{index}"
        temp_file = assets_dir / f"{title}.png.mmd"
        
        if temp_file.exists():
            mermaid_code = temp_file.read_text()
            results.append((title, mermaid_code))
    
    return results


def convert_mermaid_to_svg(mermaid_code: str, output_path: Path) -> bool:
    """Convert Mermaid code to SVG using mermaid-cli."""
    # Create temporary mermaid file
    temp_mmd = output_path.parent / f"{output_path.stem}_temp.mmd"
    
    try:
        # Write mermaid code to temp file
        temp_mmd.write_text(mermaid_code)
        
        # Run mermaid-cli to convert to SVG
        # Using npx to automatically install if needed
        cmd = [
            'npx', '-y', '@mermaid-js/mermaid-cli',
            '-i', str(temp_mmd),
            '-o', str(output_path),
            '-b', 'transparent',
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
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


def update_markdown_with_svg(md_file: Path, title: str, svg_rel_path: str):
    """Replace PNG image reference with SVG for better quality with click-zoom."""
    content = md_file.read_text()
    
    # Look for the PNG image line and replace .png with .svg
    png_pattern = r'(!\[' + re.escape(title) + r' diagram\]\([^\)]+)\.png(\)\{[^}]+\})'
    
    # Replace PNG with SVG, keeping all other attributes
    new_content = re.sub(png_pattern, r'\1.svg\2', content)
    
    if new_content != content:
        md_file.write_text(new_content)
        return True
    
    return False


def process_docs(docs_dir: Path = Path('docs/schema'), assets_dir: Path = Path('docs/assets/diagrams')):
    """Process all markdown files in docs directory."""
    
    # Create assets directory if it doesn't exist
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all markdown files with Mermaid diagrams
    md_files = list(docs_dir.glob('*.md'))
    
    total_converted = 0
    
    for md_file in md_files:
        print(f"Processing {md_file.name}...")
        
        # Extract mermaid blocks
        mermaid_blocks = extract_mermaid_blocks(md_file)
        
        if not mermaid_blocks:
            print("  No Mermaid diagrams found")
            continue
        
        for title, mermaid_code in mermaid_blocks:
            # Generate SVG filename
            svg_filename = f"{title}.svg"
            svg_path = assets_dir / svg_filename
            
            print(f"  Converting {title} to SVG...")
            
            # Convert to SVG
            if convert_mermaid_to_svg(mermaid_code, svg_path):
                # Calculate relative path from md_file to SVG
                svg_rel_path = f"../assets/diagrams/{svg_filename}"
                
                # Update markdown to use SVG instead of PNG
                if update_markdown_with_svg(md_file, title, svg_rel_path):
                    print(f"  ✓ Converted and updated to use {svg_filename}")
                    total_converted += 1
                else:
                    print(f"  ! Converted {svg_filename} but couldn't update markdown")
            else:
                print(f"  ✗ Failed to convert {title}")
    
    print(f"\nTotal diagrams converted to SVG: {total_converted}")
    return total_converted


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert Mermaid diagrams to interactive SVG')
    parser.add_argument('--docs-dir', type=Path, default=Path('docs/schema'),
                        help='Directory containing markdown files')
    parser.add_argument('--assets-dir', type=Path, default=Path('docs/assets/diagrams'),
                        help='Directory to save SVG files')
    
    args = parser.parse_args()
    
    try:
        process_docs(args.docs_dir, args.assets_dir)
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(1)
