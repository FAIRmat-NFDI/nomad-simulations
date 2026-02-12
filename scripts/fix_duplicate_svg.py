#!/usr/bin/env python3
"""Remove duplicate SVG blocks from markdown files."""

import re
from pathlib import Path


def remove_duplicate_svg_blocks(md_file: Path):
    """Remove duplicate SVG blocks, keeping only the first one for each diagram."""
    content = md_file.read_text()

    # Pattern to match the SVG block including the note admonition
    svg_block_pattern = (
        r'!!! note "High-Quality Zoomable Diagram"\s+For complex diagrams.*?</div>\s*\n'
    )

    # Find all SVG blocks
    blocks = list(re.finditer(svg_block_pattern, content, re.DOTALL))

    if len(blocks) <= 1:
        return False  # No duplicates

    # Track which diagrams we've seen
    seen_diagrams = set()
    blocks_to_remove = []

    for block in blocks:
        # Extract diagram name
        match = re.search(r'data-diagram="([^"]+)"', block.group())
        if match:
            diagram_name = match.group(1)
            if diagram_name in seen_diagrams:
                # This is a duplicate
                blocks_to_remove.append(block)
            else:
                seen_diagrams.add(diagram_name)

    # Remove duplicates (in reverse order to preserve positions)
    for block in reversed(blocks_to_remove):
        content = content[: block.start()] + content[block.end() :]

    if blocks_to_remove:
        md_file.write_text(content)
        return True

    return False


def main():
    docs_dir = Path('docs/schema')

    print('Removing duplicate SVG blocks...')
    fixed_count = 0

    for md_file in docs_dir.glob('*.md'):
        if remove_duplicate_svg_blocks(md_file):
            print(f'  Fixed: {md_file.name}')
            fixed_count += 1

    print(f'\nTotal files fixed: {fixed_count}')


if __name__ == '__main__':
    main()
