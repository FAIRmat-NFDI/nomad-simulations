# scripts/gen_diagrams.py
"""
Generate mermaid classDiagram markdown files for NOMAD schema verticals.

BACKUP & RESTORATION NOTES:
---------------------------
A backup of the original version is saved as: scripts/gen_diagrams.py.backup

To restore UML-style labels and boxes with attributes/methods sections:
1. Change class definition format:
   FROM: class {ClassName} { }
   TO:   class {ClassName}

2. Remove or modify the normalize_label() function to keep all labels:
   FROM: if label_normalized == target_normalized: return ''
   TO:   return label  # Keep all labels

3. Optionally add attributes/methods to classes:
   class {ClassName} {
       +attribute_name: Type
       +method_name()
   }

Current simplified format removes:
- Redundant edge labels (when label matches target class name)
- Empty UML attribute/method sections (uses empty braces {})
"""

from __future__ import annotations
import argparse
from pathlib import Path
import sys

# Ensure we can import sibling modules (verticals.py, meta_introspect.py)
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from verticals import VERTICALS
except Exception as e:
    raise SystemExit(
        '[gen_diagrams] Could not import VERTICALS from scripts/verticals.py.\n'
        f'Error: {e}\n'
        'Make sure you have a scripts/verticals.py that defines VERTICALS = {...} '
        'and that you are running this from the repo root: `python scripts/gen_diagrams.py`.'
    )

try:
    from meta_introspect import collect_edges
except Exception as e:
    raise SystemExit(
        '[gen_diagrams] Could not import collect_edges from scripts/meta_introspect.py.\n'
        f'Error: {e}'
    )


def find_connected_components(nodes: set[str], all_edges: dict) -> list[set[str]]:
    """
    Find disconnected subgraphs in the diagram.
    Returns a list of node sets, one for each connected component.
    """
    # Build adjacency list
    adj = {n: set() for n in nodes}
    for edge_type in ['contain', 'refs', 'inherit']:
        for a, b, _ in all_edges.get(edge_type, []):
            if a in nodes and b in nodes:
                adj[a].add(b)
                adj[b].add(a)

    # DFS to find connected components
    visited = set()
    components = []

    def dfs(node, component):
        visited.add(node)
        component.add(node)
        for neighbor in adj[node]:
            if neighbor not in visited:
                dfs(neighbor, component)

    for node in nodes:
        if node not in visited:
            component = set()
            dfs(node, component)
            components.append(component)

    return components


def filter_edges_for_vertical(
    vert_key: str,
    allowlist: list[str],
    all_edges: dict,
    verticals_dict: dict,
) -> dict:
    """
    Filter edges according to vertical-specific design rules:
    1. Don't show connections FROM child to parent sections (redundant - shown on parent page)
    2. DO show connections FROM parent to child sections (documenting the parent's structure)
    3. Show inheriting subclasses but not their subsections

    Returns filtered edges dict with 'contain', 'refs', 'inherit' keys.
    """
    # Get all classes that have their own verticals/pages
    classes_with_pages = set()
    for v_spec in verticals_dict.values():
        if isinstance(v_spec, dict):
            classes_with_pages.update(v_spec.get('sections', []))
        else:
            classes_with_pages.update(v_spec)

    # Parent sections that children should not show connections TO
    parent_sections = {
        'Simulation',
        'BaseSimulation',
        'ModelSystem',
        'ModelMethod',
        'Outputs',
    }

    allowlist_set = set(allowlist)
    filtered = {'contain': [], 'refs': [], 'inherit': []}

    # Filter containment edges
    for a, b, label in all_edges.get('contain', []):
        # Only process edges where source is in this vertical's allowlist
        if a not in allowlist_set:
            continue

        # If source is a parent section (Simulation, etc), show all its direct children
        if a in parent_sections and a in allowlist_set:
            filtered['contain'].append((a, b, label))
            continue

        # For non-parent sections: exclude connections to parent sections
        if b in parent_sections and b not in allowlist_set:
            continue

        # Exclude connections to classes that have their own pages (unless both in allowlist)
        if b in classes_with_pages and b not in allowlist_set:
            continue

        # Include everything else
        filtered['contain'].append((a, b, label))

    # Filter reference edges
    for a, b, label in all_edges.get('refs', []):
        if a in allowlist_set and b in allowlist_set:
            filtered['refs'].append((a, b, label))

    # Filter inheritance edges - always show if both are in allowlist
    for a, b, _ in all_edges.get('inherit', []):
        if a in allowlist_set and b in allowlist_set:
            filtered['inherit'].append((a, b, ''))

    return filtered


def categorize_nodes(nodes: set[str], all_edges: dict, allowlist: list[str]) -> dict:
    """
    Categorize nodes into:
    - root_connectors: nodes that connect to higher-level classes (Simulation, etc.)
    - inheritance_trees: nodes involved in inheritance relationships
    - isolated: nodes with no special categorization
    """
    # Find nodes that have edges to high-level classes not in allowlist
    root_classes = {
        'Simulation',
        'BaseSimulation',
        'Outputs',
        'ModelSystem',
        'ModelMethod',
    }
    root_connectors = set()

    for edge_type in ['contain', 'refs']:
        for a, b, _ in all_edges.get(edge_type, []):
            if a in allowlist and b in root_classes and b not in allowlist:
                root_connectors.add(a)
            if b in allowlist and a in root_classes and a not in allowlist:
                root_connectors.add(b)
            # Also include nodes that reference Simulation, etc.
            if a in allowlist and a in nodes:
                for _, target, _ in all_edges.get('refs', []):
                    if target in root_classes:
                        root_connectors.add(a)

    # Find inheritance relationships
    inheritance_nodes = set()
    for a, b, _ in all_edges.get('inherit', []):
        if a in nodes or b in nodes:
            inheritance_nodes.add(a)
            inheritance_nodes.add(b)

    return {
        'root_connectors': root_connectors & nodes,
        'inheritance_nodes': inheritance_nodes & nodes,
        'all_nodes': nodes,
    }


def mermaid_for_vertical(
    name: str,
    allowlist: list[str],
    all_edges: dict,
    add_header: bool = False,
    key: str = '',
    verticals_dict: dict = None,
) -> str:
    """
    Build Mermaid classDiagram(s) for a vertical with improved organization:
    1. Show inheritance explicitly using <|--
    2. Separate disconnected components into different diagrams
    3. Organize hierarchically: root connections first, then detailed inheritance
    4. Filter edges per vertical design rules (no parent connections, no child subsections)
    """
    # Apply vertical-specific filtering if verticals dict provided
    if verticals_dict:
        filtered_edges = filter_edges_for_vertical(
            key, allowlist, all_edges, verticals_dict
        )
    else:
        filtered_edges = all_edges

    nodes = set(allowlist)
    for edge_type in ['contain', 'refs', 'inherit']:
        for a, b, _ in filtered_edges.get(edge_type, []):
            if a in allowlist or b in allowlist:
                nodes.update([a, b])

    lines = []
    if add_header:
        lines.extend(
            [
                f'# {name} - Full Screen Diagram',
                '',
                '!!! tip "Interactive Zoom & Pan"',
                '    - **Scroll wheel** or **+/-** buttons to zoom',
                '    - **Click and drag** to pan',
                '    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit',
                '    - **↗** button to open in separate window',
                '    - **⬇** button to download as SVG',
                '',
                'This diagram shows the relationships between schema classes:',
                '',
                '- **Solid arrows** (-->) represent SubSection containment',
                '- **Dashed arrows** (..->) represent Quantity references',
                '- **Inheritance arrows** (<|--) represent class inheritance',
                '',
            ]
        )

    # Find connected components
    components = find_connected_components(nodes, filtered_edges)

    # Sort components by size (largest first) and if they contain root connections
    categories = categorize_nodes(nodes, filtered_edges, allowlist)

    def component_priority(comp):
        has_root = bool(comp & categories['root_connectors'])
        return (
            -len(comp & categories['root_connectors']),
            -len(comp),
            min(comp) if comp else 'z',
        )

    components.sort(key=component_priority)

    # Generate diagram(s)
    for idx, component in enumerate(components):
        if idx > 0:
            lines.extend(['', '---', ''])  # Separator between components

        lines.extend(['```mermaid', 'classDiagram'])

        # Define classes
        for n in sorted(component):
            lines.append(f'    class {n} {{')
            lines.append(f'    }}')

        # Helper function to normalize labels
        def normalize_label(label: str, target: str) -> str:
            label_normalized = label.replace('_', '').lower()
            target_normalized = target.lower()

            if label_normalized == target_normalized:
                return ''
            if label_normalized == target_normalized + 's':
                return ''
            if label_normalized + 's' == target_normalized:
                return ''
            return label

        # Add inheritance edges first (most important for understanding)
        for a, b, _ in filtered_edges.get('inherit', []):
            if a in component and b in component:
                lines.append(f'    {b} <|-- {a}')

        # Add containment edges
        for a, b, label in filtered_edges.get('contain', []):
            if a in component and b in component:
                clean_label = normalize_label(label, b)
                if clean_label:
                    lines.append(f'    {a} --> {b} : {clean_label}')
                else:
                    lines.append(f'    {a} --> {b}')

        # Add reference edges
        for a, b, label in filtered_edges.get('refs', []):
            if a in component and b in component:
                clean_label = normalize_label(label, b)
                if clean_label:
                    lines.append(f'    {a} ..> {b} : {clean_label}')
                else:
                    lines.append(f'    {a} ..> {b}')

        lines.append('```')

        # Add visual legend with inline SVG arrows
        lines.extend(
            [
                '',
                '<div style="font-size: 1em; color: #666; margin-top: 12px; margin-bottom: 12px;">',
                '<b>Legend:</b>',
                '<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="50" y1="15" x2="10" y2="15" stroke="currentColor" stroke-width="2.5"/><polygon points="10,15 20,8 20,22" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="miter"/></svg> inheritance ·',
                '<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="10" y1="15" x2="50" y2="15" stroke="currentColor" stroke-width="2.5"/><polygon points="50,15 40,8 40,22" fill="currentColor"/></svg> containment ·',
                '<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="10" y1="15" x2="50" y2="15" stroke="currentColor" stroke-width="2.5" stroke-dasharray="4,4"/><polygon points="50,15 40,8 40,22" fill="currentColor"/></svg> reference',
                '</div>',
                '',
            ]
        )

    return '\n'.join(lines)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description='Generate Mermaid diagrams for schema verticals.'
    )
    p.add_argument(
        '--pkg',
        default='nomad_simulations',
        help='Root package to introspect for edges (your plugin package).',
    )
    p.add_argument(
        '--module-prefix',
        default='nomad_simulations',
        help='Limit edges to classes under this module prefix.',
    )
    p.add_argument(
        '--out-dir',
        default='docs/schema',
        help='Directory where <vertical>.diagram.md files will be written.',
    )
    p.add_argument(
        '--stdout',
        action='store_true',
        help='Print diagrams to stdout instead of writing files.',
    )
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    edges = collect_edges(pkg=args.pkg, only_modules_prefix=args.module_prefix)

    out_dir = Path(args.out_dir)
    if not args.stdout:
        out_dir.mkdir(parents=True, exist_ok=True)

    for key, spec in VERTICALS.items():
        allowlist = list(spec['sections'])
        md = mermaid_for_vertical(
            spec.get('title', key),
            allowlist,
            edges,
            add_header=True,
            key=key,
            verticals_dict=VERTICALS,
        )

        if args.stdout:
            print(f"# {spec.get('title', key)}")
            print(md)
            print()
        else:
            out_path = out_dir / f'{key}.diagram.md'
            out_path.write_text(md, encoding='utf-8')
            print(f'[gen_diagrams] Wrote {out_path}')


if __name__ == '__main__':
    sys.exit(main())
