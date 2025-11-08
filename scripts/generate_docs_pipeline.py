#!/usr/bin/env python3
"""
Complete Documentation Generation Pipeline

This script runs the entire documentation generation workflow:
1. Generate standalone diagram pages (gen_diagrams.py)
2. Generate schema documentation pages (gen_docs.py)
3. Convert Mermaid diagrams to PNG images (mermaid_to_png.py)

Requirements:
- Python 3.10+
- Node.js/npm with npx (for Mermaid to PNG conversion)

Usage:
    python scripts/generate_docs_pipeline.py

The complete pipeline takes ~1-2 minutes depending on the number of diagrams.
"""

import subprocess
import sys
from pathlib import Path


def run_command(description: str, command: list, cwd = None) -> bool:
    """
    Run a subprocess command with progress reporting.

    Args:
        description: Human-readable description of the step
        command: Command and arguments as a list
        cwd: Working directory for the command (optional)

    Returns:
        True if successful, False otherwise
    """
    print(f'\n{"=" * 60}')
    print(f'Step: {description}')
    print(f'{"=" * 60}')
    print(f'Running: {" ".join(command)}')

    try:
        # Don't capture output - let it stream to console
        subprocess.run(command, cwd=cwd, check=True, text=True)
        print('✓ Success')
        return True
    except subprocess.CalledProcessError as e:
        print(f'✗ Error: Command failed with exit code {e.returncode}')
        return False
    except FileNotFoundError:
        print(f'✗ Error: Command not found: {command[0]}')
        return False


def check_prerequisites() -> bool:
    """Check if required tools are available."""
    print('Checking prerequisites...')

    # Check Python
    print(f'✓ Python {sys.version_info.major}.{sys.version_info.minor} found')

    # Check npx (for Mermaid conversion)
    try:
        result = subprocess.run(
            ['npx', '--version'], capture_output=True, text=True, check=True
        )
        print(f'✓ npx found (version {result.stdout.strip()})')
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print('✗ npx not found!')
        print('Please install Node.js/npm from https://nodejs.org/')
        return False


def main():
    """Run the complete documentation generation pipeline."""
    print('=' * 60)
    print('NOMAD Simulations Documentation Generation Pipeline')
    print('=' * 60)

    # Get repository root (parent of scripts directory)
    repo_root = Path(__file__).parent.parent

    # Check prerequisites
    if not check_prerequisites():
        print('\nPipeline aborted: missing prerequisites')
        sys.exit(1)

    # Step 1: Generate standalone diagram pages
    step1_success = run_command(
        description='Generate standalone diagram pages',
        command=[sys.executable, 'scripts/gen_diagrams.py'],
        cwd=repo_root,
    )

    if not step1_success:
        print('\n⚠ Warning: Diagram generation failed, but continuing...')

    # Step 2: Generate schema documentation
    step2_success = run_command(
        description='Generate schema documentation pages',
        command=[
            sys.executable,
            'scripts/gen_docs.py',
            '--pkg',
            'nomad_simulations',
            '--module-prefix',
            'nomad_simulations',
            '--templates-dir',
            'templates',
            '--out-dir',
            'docs/schema',
        ],
        cwd=repo_root,
    )

    if not step2_success:
        print('\n✗ Error: Schema documentation generation failed')
        sys.exit(1)

    # Step 3: Convert Mermaid to PNG
    step3_success = run_command(
        description='Convert Mermaid diagrams to PNG images',
        command=[sys.executable, 'scripts/mermaid_to_png.py'],
        cwd=repo_root,
    )

    if not step3_success:
        print('\n⚠ Warning: PNG conversion failed')
        print(
            'Documentation generated but diagrams are in Mermaid format (not clickable)'
        )
        sys.exit(1)
    
    # Step 4: Convert PNG references to SVG (vector graphics with click-zoom)
    print('\n' + '=' * 60)
    print('Converting PNG to SVG for vector quality')
    print('=' * 60)
    step4_success = run_command(
        description='Convert diagrams to SVG with click-zoom',
        command=[sys.executable, 'scripts/mermaid_to_svg_simple.py'],
        cwd=repo_root,
    )

    if not step4_success:
        print('\n⚠ Note: SVG conversion failed, but PNG version is available')

    # Final summary
    print('\n' + '=' * 60)
    print('Pipeline Complete!')
    print('=' * 60)
    print('\nGenerated documentation files:')
    print('  - docs/schema/index.md (overview page)')
    print('  - docs/schema/*.md (vertical domain pages)')
    print('  - docs/schema/*.diagram.md (standalone diagram pages)')
    if step4_success:
        print('  - docs/assets/diagrams/*.svg (SVG vector images with click-zoom)')
    else:
        print('  - docs/assets/diagrams/*.png (PNG images with click-zoom)')
    print('\nNext steps:')
    print('  1. Review the generated documentation:')
    print('     mkdocs serve')
    print('  2. View at http://127.0.0.1:8000')
    print('\nDiagram features:')
    if step4_success:
        print('  ✓ SVG vector graphics - infinite zoom quality')
        print('  ✓ Click to zoom (2x scale)')
        print('  ✓ Smaller file sizes than PNG')
    else:
        print('  ✓ PNG with click-to-zoom (2x scale)')


if __name__ == '__main__':
    main()
