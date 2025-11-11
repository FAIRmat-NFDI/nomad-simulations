#!/usr/bin/env python3
"""
Convert Mermaid diagrams to SVG with simple click-zoom.

This script:
1. Finds PNG references in markdown files
2. Reads the mermaid source from .png.mmd files
3. Converts them to SVG using mermaid-cli
4. Post-processes SVG to remove UML dividers for cleaner appearance
5. Updates markdown to reference SVG instead of PNG
6. Adds XML declaration for proper browser rendering

The SVG files work with the existing click-zoom JavaScript/CSS.

BACKUP NOTE: To restore UML-style boxes with dividers, comment out the
clean_svg_dividers() call in convert_mermaid_to_svg().
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


def extract_mermaid_from_md(md_file: Path):
    """Extract mermaid code blocks from markdown."""
    content = md_file.read_text()
    
    # Pattern: ```mermaid ... ```
    pattern = r'```mermaid\n(.*?)\n```'
    
    matches = re.findall(pattern, content, re.DOTALL)
    return matches


def clean_svg_dividers(svg_content: str) -> str:
    """
    Simplify UML-style boxes in mermaid classDiagram SVGs.
    
    Keeps one divider line below the class name for visual separation,
    but removes the second divider and empty attribute/method sections.
    
    To restore full UML-style boxes: comment out the call to this function in convert_mermaid_to_svg()
    
    Args:
        svg_content: The raw SVG content string
        
    Returns:
        Cleaned SVG content with simplified boxes (one divider only)
    """
    # Find all divider elements
    dividers = list(re.finditer(r'<g class="divider"[^>]*>.*?</g>', svg_content, flags=re.DOTALL))
    
    # Remove only the second divider from each class box (keeping the first one)
    # In mermaid UML boxes, there are typically 2 dividers: one after class name, one after attributes
    # We want to keep the first divider but remove the second
    if len(dividers) > 0:
        # Remove every second divider (indices 1, 3, 5, 7, ...)
        # Process in reverse order to preserve string positions
        for i in range(len(dividers) - 1, -1, -1):
            # Check if this is a second divider by counting dividers before it in the same class
            # For simplicity, remove dividers at odd indices (0-based: 1, 3, 5, ...)
            if i % 2 == 1:
                match = dividers[i]
                svg_content = svg_content[:match.start()] + svg_content[match.end():]
    
    # Remove the empty <g class="members-group"> and <g class="methods-group"> elements
    # These are not needed for display
    svg_content = re.sub(
        r'<g class="members-group"[^>]*>.*?</g>',
        '',
        svg_content,
        flags=re.DOTALL
    )
    svg_content = re.sub(
        r'<g class="methods-group"[^>]*>.*?</g>',
        '',
        svg_content,
        flags=re.DOTALL
    )
    
    return svg_content


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
            # Read the generated SVG
            svg_content = output_path.read_text()
            
            # Clean UML dividers for simpler appearance
            # BACKUP NOTE: Comment out the next line to restore UML-style boxes with dividers
            svg_content = clean_svg_dividers(svg_content)
            
            # Add XML declaration if missing
            if not svg_content.startswith('<?xml'):
                svg_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_content
            
            # Write the cleaned SVG back
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
    # Process .diagram.md files separately (they have mermaid code, not PNG refs)
    diagram_md_files = list(docs_dir.glob('*.diagram.md'))
    regular_md_files = [f for f in docs_dir.glob('*.md') if not f.name.endswith('.diagram.md')]
    
    total_converted = 0
    total_updated = 0
    
    # Process .diagram.md files - read mermaid directly from file
    for md_file in diagram_md_files:
        print(f"Processing {md_file.name}...")
        
        # Extract mermaid code blocks
        mermaid_blocks = extract_mermaid_from_md(md_file)
        
        if not mermaid_blocks:
            print("  No mermaid code blocks found")
            continue
        
        # Generate SVG for each mermaid block
        for idx, mermaid_code in enumerate(mermaid_blocks):
            # Generate TWO SVG files:
            # 1. For the .diagram.md file itself: "methods.diagram_0.svg"
            # 2. For the regular .md file: "methods_0.svg"
            
            base_name = md_file.stem  # e.g., "methods.diagram"
            
            # Full name for .diagram.md reference
            svg_filename_full = f"{base_name}_{idx}.svg"
            svg_path_full = assets_dir / svg_filename_full
            
            # Short name for regular .md reference (remove ".diagram" suffix)
            short_name = base_name.replace('.diagram', '')
            svg_filename_short = f"{short_name}_{idx}.svg"
            svg_path_short = assets_dir / svg_filename_short
            
            print(f"  Converting diagram {idx} to SVG...")
            
            # Generate full name SVG (for .diagram.md)
            if convert_mermaid_to_svg(mermaid_code, svg_path_full):
                print(f"  ✓ Generated {svg_filename_full}")
                total_converted += 1
            else:
                print(f"  ✗ Failed to convert {svg_filename_full}")
            
            # Generate short name SVG (for regular .md)
            if convert_mermaid_to_svg(mermaid_code, svg_path_short):
                print(f"  ✓ Generated {svg_filename_short}")
                total_converted += 1
            else:
                print(f"  ✗ Failed to convert {svg_filename_short}")
    
    # Process regular markdown files - read from .png.mmd files
    for md_file in regular_md_files:
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
            print("  ✓ Updated markdown to use SVG")
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
