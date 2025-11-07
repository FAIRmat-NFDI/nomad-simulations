#!/usr/bin/env python3
"""
Convert Mermaid diagrams to PNG images for click-zoom functionality.

This script:
1. Scans markdown files for Mermaid code blocks
2. Extracts them to temporary .mmd files
3. Converts them to PNG using mermaid-cli (mmdc)
4. Updates markdown to reference the PNG with click-zoom wrapper
"""

import re
import subprocess
import sys
from pathlib import Path


def extract_mermaid_blocks(md_file: Path) -> list[tuple[str, str]]:
    """Extract mermaid code blocks from markdown file.
    
    Returns list of (title, mermaid_code) tuples.
    """
    content = md_file.read_text()
    
    # Find all mermaid code blocks
    pattern = r'```mermaid\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)
    
    # Try to find a title/heading before each mermaid block
    blocks = []
    for i, mermaid_code in enumerate(matches):
        # Use the filename and index as identifier
        title = f"{md_file.stem}_{i}"
        blocks.append((title, mermaid_code))
    
    return blocks


def convert_mermaid_to_png(mermaid_code: str, output_path: Path) -> bool:
    """Convert Mermaid code to PNG using mermaid-cli.
    
    Returns True if successful, False otherwise.
    """
    # Create temporary .mmd file
    temp_mmd = output_path.with_suffix('.mmd')
    temp_mmd.write_text(mermaid_code)
    
    try:
        # Run mermaid-cli to convert to PNG
        # -b transparent: transparent background
        # -w 2000: width for high resolution
        # -s 2: scale factor for better quality
        result = subprocess.run(
            [
                'npx', '-y', '@mermaid-js/mermaid-cli@latest',
                '-i', str(temp_mmd),
                '-o', str(output_path),
                '-b', 'transparent',
                '-w', '2000',
                '-s', '2'
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"Error converting {temp_mmd}: {result.stderr}", file=sys.stderr)
            return False
        
        # Clean up temp file
        temp_mmd.unlink()
        return True
        
    except subprocess.TimeoutExpired:
        print(f"Timeout converting {temp_mmd}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def update_markdown_with_png(md_file: Path, title: str, png_rel_path: str):
    """Replace Mermaid code block with click-zoom PNG reference."""
    content = md_file.read_text()
    
    # Find the mermaid block (first occurrence for simplicity)
    pattern = r'```mermaid\n.*?```'
    
    # Use simple markdown image first to test
    replacement = f'''![{title} diagram]({png_rel_path}){{: style="width: 80%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}}'''
    
    # Replace only the first match
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    
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
            print(f"  No Mermaid diagrams found")
            continue
        
        for title, mermaid_code in mermaid_blocks:
            # Generate PNG filename
            png_filename = f"{title}.png"
            png_path = assets_dir / png_filename
            
            print(f"  Converting {title}...")
            
            # Convert to PNG
            if convert_mermaid_to_png(mermaid_code, png_path):
                # Calculate relative path from md_file to PNG
                png_rel_path = f"../assets/diagrams/{png_filename}"
                
                # Update markdown
                if update_markdown_with_png(md_file, title, png_rel_path):
                    print(f"  ✓ Converted and updated {png_filename}")
                    total_converted += 1
                else:
                    print(f"  ! Failed to update markdown for {png_filename}")
            else:
                print(f"  ✗ Failed to convert {title}")
    
    print(f"\nTotal diagrams converted: {total_converted}")
    return total_converted


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert Mermaid diagrams to PNG')
    parser.add_argument('--docs-dir', type=Path, default=Path('docs/schema'),
                        help='Directory containing markdown files')
    parser.add_argument('--assets-dir', type=Path, default=Path('docs/assets/diagrams'),
                        help='Directory to save PNG files')
    
    args = parser.parse_args()
    
    try:
        process_docs(args.docs_dir, args.assets_dir)
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(1)
