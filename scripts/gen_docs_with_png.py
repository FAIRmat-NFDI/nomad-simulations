#!/usr/bin/env python3
"""
Enhanced documentation generation with PNG diagram export.

This script:
1. Runs the normal gen_docs.py to generate markdown with Mermaid
2. Converts Mermaid diagrams to PNG for click-zoom functionality
3. Updates the templates to use PNG images
"""

import subprocess
import sys
from pathlib import Path


def run_gen_docs():
    """Run the normal documentation generation."""
    print("[gen_docs_with_png] Step 1: Generating documentation with Mermaid...")
    result = subprocess.run(
        [sys.executable, 'scripts/gen_docs.py'],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return False
    return True


def convert_mermaid_to_png():
    """Convert Mermaid diagrams to PNG."""
    print("\n[gen_docs_with_png] Step 2: Converting Mermaid diagrams to PNG...")
    result = subprocess.run(
        [sys.executable, 'scripts/mermaid_to_png.py'],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return False
    return True


def main():
    """Main workflow."""
    print("=" * 60)
    print("Documentation Generation with PNG Diagrams")
    print("=" * 60)
    
    # Step 1: Generate docs with Mermaid
    if not run_gen_docs():
        print("\n✗ Failed to generate documentation", file=sys.stderr)
        return 1
    
    # Step 2: Convert to PNG
    if not convert_mermaid_to_png():
        print("\n✗ Failed to convert diagrams to PNG", file=sys.stderr)
        print("Note: PNG conversion requires Node.js/npm to be installed", file=sys.stderr)
        return 1
    
    print("\n" + "=" * 60)
    print("✓ Documentation generated successfully with PNG diagrams!")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
