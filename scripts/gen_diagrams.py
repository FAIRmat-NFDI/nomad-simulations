# scripts/gen_diagrams.py
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


def mermaid_for_vertical(name: str, allowlist: list[str], all_edges: dict, add_header: bool = False, key: str = '') -> str:
    """
    Build a small Mermaid classDiagram for a vertical.
    Solid arrows = SubSection containment; dashed arrows = Quantity references.
    """
    nodes = set(allowlist)
    for a, b, _ in all_edges['contain'] + all_edges['refs']:
        if a in allowlist or b in allowlist:
            nodes.update([a, b])

    lines = []
    if add_header:
        lines.extend([
            f'# {name} - Full Screen Diagram',
            '',
            '!!! tip "Interactive Zoom & Pan"',
            '    - **Scroll wheel** or **+/-** buttons to zoom',
            '    - **Click and drag** to pan',
            '    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit',
            '    - **↗** button to open in separate window',
            '    - **⬇** button to download as SVG',
            '',
            'This diagram shows the relationships between schema classes in this vertical:',
            '',
            '- **Solid arrows** (-->) represent SubSection containment',
            '- **Dashed arrows** (..->) represent Quantity references',
            '',
        ])
    
    lines.extend(['```mermaid', 'classDiagram'])
    for n in sorted(nodes):
        lines.append(f'    class {n}')
    for a, b, label in all_edges['contain']:
        if a in nodes and b in nodes:
            lines.append(f'    {a} --> {b} : {label}')
    for a, b, label in all_edges['refs']:
        if a in nodes and b in nodes:
            lines.append(f'    {a} ..> {b} : {label}')
    lines.append('```')
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
        md = mermaid_for_vertical(spec.get('title', key), allowlist, edges, add_header=True, key=key)

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
