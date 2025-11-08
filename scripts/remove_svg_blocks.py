#!/usr/bin/env python3
"""Remove all SVG blocks from markdown files, keeping only PNG images."""

import re
from pathlib import Path


def remove_svg_blocks(md_file: Path):
    """Remove all SVG blocks from markdown file."""
    content = md_file.read_text()
    
    # Pattern to match the SVG block including the note admonition
    svg_block_pattern = r'\n\n!!! note "High-Quality Zoomable Diagram"\s+For complex diagrams.*?</div>\s*\n'
    
    # Remove all SVG blocks
    new_content = re.sub(svg_block_pattern, '', content, flags=re.DOTALL)
    
    if new_content != content:
        md_file.write_text(new_content)
        return True
    
    return False


def main():
    docs_dir = Path('docs/schema')
    
    print("Removing all SVG blocks from markdown files...")
    fixed_count = 0
    
    for md_file in docs_dir.glob('*.md'):
        if remove_svg_blocks(md_file):
            print(f"  Cleaned: {md_file.name}")
            fixed_count += 1
    
    print(f"\nTotal files cleaned: {fixed_count}")


if __name__ == '__main__':
    main()
