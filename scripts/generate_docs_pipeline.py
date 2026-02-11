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

# ============================================================================
# DIAGRAM ZOOM CONFIGURATION
# ============================================================================
# Toggle between 'panzoom' (advanced plugin) and 'simple' (custom JS)
# - 'panzoom': Uses mkdocs-panzoom-plugin for scroll-wheel zoom + drag pan
# - 'simple': Uses custom click-to-zoom JavaScript (fallback)
DIAGRAM_ZOOM_METHOD = 'panzoom'  # Change to 'simple' to revert to old behavior
# ============================================================================


def run_command(description: str, command: list, cwd=None) -> bool:
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
    """Update .pages and mkdocs.yml navigation to match generated verticals with hierarchical structure."""
    print('\n' + '=' * 60)
    print('Updating navigation configuration')
    print('=' * 60)

    try:
        # Import verticals to get current structure
        sys.path.insert(0, str(repo_root / 'scripts'))
        from verticals import VERTICALS

        # Define hierarchical structure: parent -> [children]
        # Based on the schema tree: Simulation contains ModelSystem, ModelMethod, Outputs
        hierarchy = {
            'simulation': [],  # Top level
            'model_system': ['cell', 'particle_state', 'symmetry', 'chemical_formula'],
            'model_method': ['numerical_settings'],
            'outputs': [
                'electronic_properties',
                'manybody_properties',
                'spectroscopy',
                'thermodynamics',
            ],
        }

        # Update .pages file in docs/schema/
        pages_file = repo_root / 'docs' / 'schema' / '.pages'
        pages_content = """# docs/schema/.pages
title: Schema Documentation
index: index.md
nav:
"""
        for vert_key in VERTICALS.keys():
            pages_content += f'  - {vert_key}.md\n'

        pages_file.write_text(pages_content, encoding='utf-8')
        print(f'✓ Updated {pages_file.name} with {len(VERTICALS)} verticals')

        # Update mkdocs.yml navigation section
        mkdocs_file = repo_root / 'mkdocs.yml'
        if mkdocs_file.exists():
            import re

            mkdocs_content = mkdocs_file.read_text(encoding='utf-8')

            # Build hierarchical nav items for Schema Navigation section
            nav_items = []
            nav_items.append('      - Overview: schema/index.md')

            # Track which verticals have been added
            added = set()

            # Add top-level parent verticals with their children
            for parent_key in ['simulation', 'model_system', 'model_method', 'outputs']:
                if parent_key not in VERTICALS:
                    continue

                parent_spec = VERTICALS[parent_key]
                parent_title = parent_spec.get(
                    'title', parent_key.replace('_', ' ').title()
                )
                children = hierarchy.get(parent_key, [])

                # Add parent with children
                if children:
                    # Parent with nested children
                    nav_items.append(f'      - {parent_title}:')
                    nav_items.append(
                        f'          - {parent_title}: schema/{parent_key}.md'
                    )

                    # Add children under parent
                    for child_key in children:
                        if child_key in VERTICALS:
                            child_spec = VERTICALS[child_key]
                            child_title = child_spec.get(
                                'title', child_key.replace('_', ' ').title()
                            )
                            nav_items.append(
                                f'          - {child_title}: schema/{child_key}.md'
                            )
                            added.add(child_key)
                else:
                    # Top-level item without children
                    nav_items.append(f'      - {parent_title}: schema/{parent_key}.md')

                added.add(parent_key)

            # Add any remaining verticals that weren't in the hierarchy
            for vert_key, vert_spec in VERTICALS.items():
                if vert_key not in added:
                    title = vert_spec.get('title', vert_key.replace('_', ' ').title())
                    nav_items.append(f'      - {title}: schema/{vert_key}.md')
                    print(
                        f'⚠ Vertical "{vert_key}" not in hierarchy - added at top level'
                    )

            new_nav_section = '\n'.join(nav_items)

            # Replace the Schema Navigation section
            # Pattern: match from "Schema Navigation:" to the next top-level nav item or closing bracket
            pattern = r'(  - Schema Navigation:\s*\n)((?:      - .*\n)*)'
            replacement = f'\\1{new_nav_section}\n'

            updated_content = re.sub(pattern, replacement, mkdocs_content)

            if updated_content != mkdocs_content:
                mkdocs_file.write_text(updated_content, encoding='utf-8')
                print(
                    f'✓ Updated mkdocs.yml Schema Navigation with hierarchical structure'
                )
                print(f'  - {len(hierarchy)} parent sections')
                print(
                    f'  - {sum(len(children) for children in hierarchy.values())} child sections'
                )
            else:
                print('⚠ Could not find Schema Navigation section in mkdocs.yml')
                print('  Please manually add vertical pages to mkdocs.yml nav section')

        return True
    except Exception as e:
        print(f'✗ Error updating navigation: {e}')
        import traceback

        traceback.print_exc()
        return False


def validate_diagram_complexity(repo_root: Path) -> bool:
    """
    Validate diagram complexity according to design rules.

    Design Rules:
    - 1-5 classes: Perfect
    - 6-15 classes: Good
    - 16-25 classes: Complex - consider splitting
    - 26+ classes: Too large - must split
    """
    print('\n' + '=' * 60)
    print('Validating diagram complexity')
    print('=' * 60)

    try:
        sys.path.insert(0, str(repo_root / 'scripts'))
        from verticals import VERTICALS
        from meta_introspect import collect_edges, iter_section_classes

        # Collect all edges to analyze inheritance depth
        pkg = 'nomad_simulations'
        all_edges = collect_edges(pkg)

        has_warnings = False
        has_errors = False

        for vert_key, spec in VERTICALS.items():
            if not isinstance(spec, dict):
                continue

            sections = spec.get('sections', [])
            num_classes = len(sections)

            # Size validation
            if num_classes <= 5:
                status = '✓ Perfect'
                level = 'good'
            elif num_classes <= 15:
                status = '✓ Good'
                level = 'good'
            elif num_classes <= 25:
                status = '⚠ Complex - consider splitting'
                level = 'warning'
                has_warnings = True
            else:
                status = '✗ TOO LARGE - must split into multiple verticals'
                level = 'error'
                has_errors = True

            # Calculate inheritance depth for this vertical
            inheritance_edges = all_edges.get('inherit', [])
            vert_classes = set(sections)

            # Build inheritance tree
            children_map = {}
            for parent, child, _ in inheritance_edges:
                if parent in vert_classes and child in vert_classes:
                    if parent not in children_map:
                        children_map[parent] = []
                    children_map[parent].append(child)

            # Find max depth using BFS
            max_depth = 0
            if children_map:
                # Find root classes (those that are not children)
                all_children = set()
                for children_list in children_map.values():
                    all_children.update(children_list)
                roots = vert_classes - all_children

                # BFS from each root
                for root in roots:
                    queue = [(root, 1)]
                    visited = {root}
                    while queue:
                        node, depth = queue.pop(0)
                        max_depth = max(max_depth, depth)
                        for child in children_map.get(node, []):
                            if child not in visited:
                                visited.add(child)
                                queue.append((child, depth + 1))

            depth_status = ''
            if max_depth > 3:
                depth_status = f' | Depth: {max_depth} levels (>3, consider splitting)'
                has_warnings = True
            elif max_depth > 0:
                depth_status = f' | Depth: {max_depth} levels'

            # Print status
            if level == 'error':
                print(f'  {vert_key}: {num_classes} classes - {status}{depth_status}')
            elif level == 'warning':
                print(f'  {vert_key}: {num_classes} classes - {status}{depth_status}')
            elif num_classes > 10 or max_depth > 2:
                # Show larger verticals even if still "good"
                print(f'  {vert_key}: {num_classes} classes - {status}{depth_status}')

        # Summary
        print()
        if has_errors:
            print('✗ Some verticals are too large and must be split')
            print(
                '  See scripts/README.md "Managing Diagram Complexity" for guidelines'
            )
            return False
        elif has_warnings:
            print(
                '⚠ Some verticals are complex - consider splitting for better readability'
            )
            print('  Complexity is acceptable but could be improved')
            return True
        else:
            print('✓ All diagrams have good complexity')
            return True

    except Exception as e:
        print(f'✗ Error validating complexity: {e}')
        import traceback

        traceback.print_exc()
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
            print(
                f'⚠ Orphaned pages (not in verticals.py): {", ".join(orphaned_pages)}'
            )
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


def configure_diagram_zoom(repo_root: Path, method: str) -> bool:
    """Configure mkdocs.yml for the selected diagram zoom method."""
    print('\n' + '=' * 60)
    print(f'Configuring diagram zoom method: {method}')
    print('=' * 60)

    mkdocs_file = repo_root / 'mkdocs.yml'
    if not mkdocs_file.exists():
        print('✗ mkdocs.yml not found')
        return False

    try:
        import re
        content = mkdocs_file.read_text(encoding='utf-8')

        if method == 'panzoom':
            # Add panzoom plugin if not present
            if 'panzoom' not in content:
                # Add after search plugin (no additional config needed - works by default)
                content = re.sub(
                    r'(plugins:\s*\n\s*- search)',
                    r'\1\n  - panzoom',
                    content
                )
                print('✓ Added panzoom plugin to mkdocs.yml')
            
            # Comment out custom zoom JS
            content = re.sub(
                r"^(\s*- assets/click-zoom\.js)$",
                r"  # \1  # Disabled: using panzoom plugin",
                content,
                flags=re.MULTILINE
            )
            content = re.sub(
                r"^(\s*- assets/svg-pan-zoom-diagram\.js)$",
                r"  # \1  # Disabled: using panzoom plugin",
                content,
                flags=re.MULTILINE
            )
            
            # Comment out custom zoom CSS
            content = re.sub(
                r"^(\s*- stylesheets/mermaid-zoom\.css)$",
                r"  # \1  # Disabled: using panzoom plugin",
                content,
                flags=re.MULTILINE
            )
            content = re.sub(
                r"^(\s*- stylesheets/svg-diagram\.css)$",
                r"  # \1  # Disabled: using panzoom plugin",
                content,
                flags=re.MULTILINE
            )
            
            print('✓ Enabled panzoom plugin, disabled custom zoom JS/CSS')

        else:  # simple method
            # Remove or comment out panzoom plugin
            content = re.sub(
                r'^(\s*- panzoom:.*?)$',
                r'  # \1  # Disabled: using simple click-zoom',
                content,
                flags=re.MULTILINE | re.DOTALL
            )
            content = re.sub(
                r'^(\s*default_enable:.*?)$',
                r'  # \1',
                content,
                flags=re.MULTILINE
            )
            
            # Uncomment custom zoom JS
            content = re.sub(
                r"^\s*#\s*(- assets/click-zoom\.js).*$",
                r"  \1",
                content,
                flags=re.MULTILINE
            )
            content = re.sub(
                r"^\s*#\s*(- assets/svg-pan-zoom-diagram\.js).*$",
                r"  \1",
                content,
                flags=re.MULTILINE
            )
            
            # Uncomment custom zoom CSS
            content = re.sub(
                r"^\s*#\s*(- stylesheets/mermaid-zoom\.css).*$",
                r"  \1",
                content,
                flags=re.MULTILINE
            )
            content = re.sub(
                r"^\s*#\s*(- stylesheets/svg-diagram\.css).*$",
                r"  \1",
                content,
                flags=re.MULTILINE
            )
            
            print('✓ Enabled simple click-zoom, disabled panzoom plugin')

        mkdocs_file.write_text(content, encoding='utf-8')
        return True

    except Exception as e:
        print(f'✗ Error configuring zoom method: {e}')
        import traceback
        traceback.print_exc()
        return False


def check_prerequisites() -> bool:
    """Check if required tools are available."""
    print('Checking prerequisites...')

    # Check Python
    print(f'✓ Python {sys.version_info.major}.{sys.version_info.minor} found')

    # Check for panzoom plugin if needed
    if DIAGRAM_ZOOM_METHOD == 'panzoom':
        try:
            import importlib.util
            spec = importlib.util.find_spec('mkdocs_panzoom_plugin')
            if spec is None:
                print('⚠ mkdocs-panzoom-plugin not found')
                print('  Install with: pip install mkdocs-panzoom-plugin')
                print('  Or switch to simple mode by changing DIAGRAM_ZOOM_METHOD')
                return False
            print('✓ mkdocs-panzoom-plugin found')
        except Exception as e:
            print(f'⚠ Could not check for panzoom plugin: {e}')

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


    # Step 3/4: Image generation (only for simple mode)
    if DIAGRAM_ZOOM_METHOD == 'simple':
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
    else:
        step3_success = True
        step4_success = False  # No SVGs generated in panzoom mode

    # Step 5: Configure diagram zoom method
    step5_success = configure_diagram_zoom(repo_root, DIAGRAM_ZOOM_METHOD)

    if not step5_success:
        print('\n⚠ Warning: Diagram zoom configuration failed')

    # Step 6: Update navigation files
    step6_success = update_navigation_files(repo_root)

    if not step6_success:
        print('\n⚠ Warning: Navigation update failed')

    # Step 7: Validate diagram complexity
    step7_success = validate_diagram_complexity(repo_root)

    if not step7_success:
        print('\n⚠ Warning: Some diagrams are too complex')
        print('  See output above for details and splitting recommendations')

    # Step 8: Validate navigation consistency
    step8_success = validate_navigation(repo_root)

    if not step8_success:
        print('\n⚠ Warning: Navigation validation found issues')

    # Final summary
    print('\n' + '=' * 60)
    print('Pipeline Complete!')
    print('=' * 60)
    print('\nGenerated documentation files:')
    print('  - docs/schema/index.md (overview page)')
    print('  - docs/schema/*.md (vertical domain pages)')
    print('  - docs/schema/*.diagram.md (standalone diagram pages)')
    if DIAGRAM_ZOOM_METHOD == 'simple':
        if step4_success:
            print('  - docs/assets/diagrams/*.svg (SVG vector images)')
        else:
            print('  - docs/assets/diagrams/*.png (PNG images)')
    else:
        print('  - (No PNG/SVG images generated; using Mermaid diagrams with panzoom)')
    print('\nNext steps:')
    print('  1. Review the generated documentation:')
    print('     mkdocs serve')
    print('  2. View at http://127.0.0.1:8000')
    print('\nDiagram features:')
    if DIAGRAM_ZOOM_METHOD == 'panzoom':
        print('  ✓ Pan/Zoom Mode: mkdocs-panzoom-plugin')
        print('  ✓ Scroll-wheel zoom + drag to pan')
        print('  ✓ Fullscreen mode available')
        print('  ✓ Works with SVG vector graphics')
        print('\n  To switch to simple mode: Set DIAGRAM_ZOOM_METHOD="simple" in generate_docs_pipeline.py')
    else:
        print('  ✓ Simple Mode: Custom click-to-zoom JavaScript')
        print('  ✓ Click to zoom (2x scale)')
        if step4_success:
            print('  ✓ SVG vector graphics - infinite zoom quality')
        else:
            print('  ✓ PNG images')
        print('\n  To enable advanced pan/zoom: Set DIAGRAM_ZOOM_METHOD="panzoom" in generate_docs_pipeline.py')

    # Complexity warnings in summary
    if not step7_success:
        print('\n⚠ COMPLEXITY WARNING:')
        print('  Some verticals exceed recommended size (>25 classes)')
        print('  Consider splitting them for better readability')
        print('  See scripts/README.md "Managing Diagram Complexity"')


if __name__ == '__main__':
    main()
