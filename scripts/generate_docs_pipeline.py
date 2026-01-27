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
import shutil


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


def update_navigation_files(repo_root: Path) -> bool:
    """Update .pages and mkdocs.yml navigation to match generated verticals."""
    print('\n' + '=' * 60)
    print('Updating navigation configuration')
    print('=' * 60)
    
    try:
        # Import verticals to get current structure
        sys.path.insert(0, str(repo_root / 'scripts'))
        from verticals import VERTICALS
        
        # Update .pages file in docs/schema/
        pages_file = repo_root / 'docs' / 'schema' / '.pages'
        pages_content = '''# docs/schema/.pages
title: Schema Documentation
index: index.md
nav:
'''
        for vert_key in VERTICALS.keys():
            pages_content += f'  - {vert_key}.md\n'
        
        pages_file.write_text(pages_content, encoding='utf-8')
        print(f'✓ Updated {pages_file.name} with {len(VERTICALS)} verticals')
        
        # Validate that mkdocs.yml exists (manual update recommended)
        mkdocs_file = repo_root / 'mkdocs.yml'
        if mkdocs_file.exists():
            print('ℹ Note: Please manually verify mkdocs.yml "Schema Navigation" section')
            print('  matches the generated pages in docs/schema/')
        
        return True
    except Exception as e:
        print(f'✗ Error updating navigation: {e}')
        return False


def validate_navigation(repo_root: Path) -> bool:
    """Validate that navigation matches generated pages."""
    print('\n' + '=' * 60)
    print('Validating navigation consistency')
    print('=' * 60)
    
    try:
        # Import verticals
        sys.path.insert(0, str(repo_root / 'scripts'))
        from verticals import VERTICALS
        
        docs_schema_dir = repo_root / 'docs' / 'schema'
        
        # Check that all vertical pages exist
        missing_pages = []
        for vert_key in VERTICALS.keys():
            page_file = docs_schema_dir / f'{vert_key}.md'
            diagram_file = docs_schema_dir / f'{vert_key}.diagram.md'
            
            if not page_file.exists():
                missing_pages.append(f'{vert_key}.md')
            if not diagram_file.exists():
                missing_pages.append(f'{vert_key}.diagram.md')
        
        # Check for orphaned pages (exist but not in VERTICALS)
        orphaned_pages = []
        for md_file in docs_schema_dir.glob('*.md'):
            if md_file.name in ['index.md']:
                continue
            base_name = md_file.stem.replace('.diagram', '')
            if base_name not in VERTICALS and not md_file.name.endswith('.diagram.md'):
                orphaned_pages.append(md_file.name)
        
        # Report results
        if missing_pages:
            print(f'✗ Missing pages: {", ".join(missing_pages)}')
            return False
        
        if orphaned_pages:
            print(f'⚠ Orphaned pages (not in verticals.py): {", ".join(orphaned_pages)}')
            print('  Consider removing these manually')
        
        print(f'✓ All {len(VERTICALS)} verticals have corresponding pages')
        print('✓ Navigation is consistent')
        return True
        
    except Exception as e:
        print(f'✗ Error validating navigation: {e}')
        return False


def clean_old_docs(repo_root: Path) -> bool:
    """Remove old generated documentation files before regeneration."""
    print('\n' + '=' * 60)
    print('Cleaning old generated documentation files')
    print('=' * 60)
    
    docs_schema_dir = repo_root / 'docs' / 'schema'
    
    if not docs_schema_dir.exists():
        print('✓ No old docs to clean')
        return True
    
    try:
        # Import verticals to know which files are generated
        sys.path.insert(0, str(repo_root / 'scripts'))
        from verticals import VERTICALS
        
        # Only remove files that are generated by the script
        removed_count = 0
        
        # Remove index.md (always generated)
        index_file = docs_schema_dir / 'index.md'
        if index_file.exists():
            index_file.unlink()
            removed_count += 1
            print(f'  Removed: {index_file.name}')
        
        # Remove vertical pages and diagram pages based on VERTICALS
        for vert_key in VERTICALS.keys():
            # Remove the main vertical page
            vert_file = docs_schema_dir / f'{vert_key}.md'
            if vert_file.exists():
                vert_file.unlink()
                removed_count += 1
                print(f'  Removed: {vert_file.name}')
            
            # Remove the diagram page
            diagram_file = docs_schema_dir / f'{vert_key}.diagram.md'
            if diagram_file.exists():
                diagram_file.unlink()
                removed_count += 1
                print(f'  Removed: {diagram_file.name}')
        
        # Clean old diagram images
        assets_diagrams = repo_root / 'docs' / 'assets' / 'diagrams'
        if assets_diagrams.exists():
            shutil.rmtree(assets_diagrams)
            print(f'  Removed: docs/assets/diagrams/')
        
        print(f'✓ Cleaned {removed_count} generated documentation files')
        print('  (Manual files in docs/schema/ were preserved)')
        return True
    except Exception as e:
        print(f'✗ Error during cleanup: {e}')
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

    # Step 0: Clean old documentation files
    if not clean_old_docs(repo_root):
        print('\n⚠ Warning: Cleanup failed, but continuing...')

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

    # Step 5: Update navigation files
    step5_success = update_navigation_files(repo_root)
    
    if not step5_success:
        print('\n⚠ Warning: Navigation update failed')

    # Step 6: Validate navigation consistency
    step6_success = validate_navigation(repo_root)
    
    if not step6_success:
        print('\n⚠ Warning: Navigation validation found issues')

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
