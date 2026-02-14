#!/usr/bin/env python3
"""Clean up any SVG-related HTML fragments from markdown files."""

import re
from pathlib import Path


def clean_svg_remnants(md_file: Path):
    """Remove any SVG-related HTML fragments."""
    content = md_file.read_text()
    original_content = content

    # Remove embed tags
    content = re.sub(r'\s*<embed[^>]*class="interactive-svg"[^>]*/?>\s*', '', content)

    # Remove orphaned closing div tags
    content = re.sub(r'\s*</div>\s*\n\s*\n', '\n\n', content)

    # Remove diagram-container divs
    content = re.sub(
        r'\s*<div class="diagram-container"[^>]*>.*?</div>\s*',
        '',
        content,
        flags=re.DOTALL,
    )

    # Remove diagram-hint divs
    content = re.sub(
        r'\s*<div class="diagram-hint">.*?</div>\s*', '', content, flags=re.DOTALL
    )

    # Clean up multiple consecutive blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    if content != original_content:
        md_file.write_text(content)
        return True

    return False


def main():
    docs_dir = Path('docs/schema')

    print('Cleaning up SVG remnants from markdown files...')
    fixed_count = 0

    for md_file in docs_dir.glob('*.md'):
        if clean_svg_remnants(md_file):
            print(f'  Cleaned: {md_file.name}')
            fixed_count += 1

    print(f'\nTotal files cleaned: {fixed_count}')


if __name__ == '__main__':
    main()
