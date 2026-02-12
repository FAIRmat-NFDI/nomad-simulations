# scripts/gen_docs.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# Ensure sibling imports work when run from repo root
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from gen_diagrams import filter_edges_for_vertical
from jinja2 import Environment, FileSystemLoader, select_autoescape
from meta_introspect import collect_edges, iter_section_classes
from verticals import VERTICALS

# ---- optional: richer example generator if present --------------------------
try:
    from gen_examples import example_for_section  # should accept an MSection class
except Exception:

    def example_for_section(section_cls, depth: int = 1):
        """
        Minimal fallback: emits nulls for quantities and stubs for subsections.
        """
        from nomad.metainfo import MSection

        if not isinstance(section_cls, type) or not issubclass(section_cls, MSection):
            raise RuntimeError(
                'Fallback example_for_section expects an MSection class.'
            )
        sdef = section_cls.m_def
        data = {}
        for q in getattr(sdef, 'quantities', []):
            default = getattr(q, 'default', None)
            data[q.name] = default if default is not None else None
        if depth > 0:
            for ss in getattr(sdef, 'sub_sections', []):
                data[ss.name] = [{}] if getattr(ss, 'repeats', False) else {}
        return data


# ---- helpers ----------------------------------------------------------------


def clean_scope_item(item: str) -> str:
    """Remove (see ...) parenthetical references from scope items."""
    import re

    return re.sub(r'\s*\(see\s+[^)]+\)', '', item).strip()


def collect_quantities_info(section_cls) -> list[dict]:
    """Collect quantity names, types, and docstrings from a section class."""
    from nomad.metainfo import MSection

    if not isinstance(section_cls, type) or not issubclass(section_cls, MSection):
        return []

    sdef = section_cls.m_def
    quantities_info = []

    for q in getattr(sdef, 'quantities', []):
        # Get quantity name
        name = q.name

        # Get type information
        type_str = 'Any'
        if hasattr(q, 'type'):
            q_type = q.type
            if hasattr(q_type, '__name__'):
                type_str = q_type.__name__
            else:
                type_str = str(q_type)

        # Get shape information if it's an array
        shape_str = ''
        if hasattr(q, 'shape') and q.shape:
            shape_str = f' (shape: {q.shape})'

        # Get docstring/description
        description = ''
        if hasattr(q, 'description') and q.description:
            description = q.description.strip()
        elif hasattr(q, '__doc__') and q.__doc__:
            description = q.__doc__.strip()

        # Clean description for markdown table:
        if description:
            import re

            # Split into lines and clean
            lines = description.split('\n')
            cleaned_lines = [line.strip() for line in lines if line.strip()]

            # Check if this is a complex multi-paragraph/multi-line description
            # Complex = has blank lines separating paragraphs OR has multiple lines
            has_multiple_paragraphs = len(cleaned_lines) > 3

            if has_multiple_paragraphs:
                # Use collapsible details for complex descriptions
                # Extract first sentence as summary
                first_line = cleaned_lines[0]
                match = re.match(r'^(.*?[.!?])\s', first_line + ' ')
                if match:
                    summary = match.group(1)
                else:
                    # No sentence boundary, use first line or truncate
                    summary = first_line[:80] + ('...' if len(first_line) > 80 else '')

                # Build full description with proper formatting
                # Escape pipes and preserve structure
                full_text_lines = []
                for line in cleaned_lines:
                    # Escape pipes
                    escaped_line = line.replace('|', '\\|')
                    full_text_lines.append(escaped_line)

                full_text = '<br>'.join(full_text_lines)

                # Create collapsible element
                description = (
                    f'<details><summary>{summary}</summary>{full_text}</details>'
                )
            else:
                # Simple description: join lines with space
                description = ' '.join(cleaned_lines)
                # Escape any pipe characters that might break the table
                description = description.replace('|', '\\|')

        # Combine type and shape
        full_type = type_str + shape_str

        quantities_info.append(
            {
                'name': name,
                'type': full_type,
                'description': description
                if description
                else 'No description available.',
            }
        )

    return quantities_info


def build_registry(
    pkg: str, extra_modules: list[str] | None = None
) -> dict[str, object]:
    """Map {ClassName -> MSection subclass} discovered under the package."""
    import importlib
    import inspect

    from nomad.metainfo import MSection

    reg: dict[str, object] = {}
    for cls in iter_section_classes(pkg):
        reg[cls.__name__] = cls

    if extra_modules:
        for mod_name in extra_modules:
            try:
                mod = importlib.import_module(mod_name)
            except Exception:
                continue
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                try:
                    if issubclass(obj, MSection) and obj is not MSection:
                        reg[obj.__name__] = obj
                except Exception:
                    continue
    return reg


def resolve_section_classes(
    names: list[str], registry: dict[str, object]
) -> list[object]:
    missing = [n for n in names if n not in registry]
    if missing:
        available = ', '.join(sorted(registry.keys()))
        raise SystemExit(
            '[gen_docs] Could not resolve section classes for: '
            + ', '.join(missing)
            + f'.\nAvailable classes I can see: {available}\n'
            "Check VERTICALS['...']['sections'] names or extend search modules."
        )
    return [registry[n] for n in names]


def mermaid_for_vertical(
    title: str,
    allowlist: list[str],
    edges: dict,
    vert_key: str = None,
    verticals_dict: dict = None,
) -> str:
    """
    Emit a properly fenced Mermaid block (with leading/trailing blank lines),
    so MkDocs/Material v9 renders it without any extra JS.
    Shows inheritance, containment, and reference relationships.
    Applies filtering to exclude parent connections and child subsections.
    """
    # Apply vertical-specific filtering if verticals dict and key provided
    if verticals_dict and vert_key:
        filtered_edges = filter_edges_for_vertical(
            vert_key, allowlist, edges, verticals_dict
        )
    else:
        filtered_edges = edges

    nodes = set(allowlist)
    for edge_type in ['contain', 'refs', 'inherit']:
        for a, b, _ in filtered_edges.get(edge_type, []):
            if a in allowlist or b in allowlist:
                nodes.update([a, b])

    lines = []
    lines.append('```mermaid')
    lines.append('classDiagram')
    for n in sorted(nodes):
        lines.append(f'    class {n}')

    # Add inheritance edges first (most important)
    for a, b, _ in filtered_edges.get('inherit', []):
        if a in nodes and b in nodes:
            lines.append(f'    {b} <|-- {a}')

    # Add containment edges
    for a, b, label in filtered_edges.get('contain', []):
        if a == b:
            continue
        if a in nodes and b in nodes:
            lines.append(f'    {a} --> {b} : {label}')

    # Add reference edges
    for a, b, label in filtered_edges.get('refs', []):
        if a == b:
            continue
        if a in nodes and b in nodes:
            lines.append(f'    {a} ..> {b} : {label}')

    # Add one summarized anchor relation for outputs diagrams:
    # many output sections derive from PhysicalProperty, but drawing every
    # inheritance edge here would make the diagram too dense.
    if vert_key == 'outputs' and 'Outputs' in nodes and 'PhysicalProperty' in nodes:
        lines.append('    Outputs ..> PhysicalProperty : base type for most outputs')
    lines.append('```')
    # Wrap with blank lines (very important for Markdown parsing)
    diagram = '\n' + '\n'.join(lines) + '\n'
    # Use notation-based legend to avoid arrow-direction ambiguity.
    diagram += """
**Legend**

- `Parent <|-- Child`: inheritance (`Child` extends `Parent`)
- `Owner --> SubSection`: containment/subsection relationship
- `Source ..> Target`: typed reference from one section to another
"""
    return diagram


# ---- main generation --------------------------------------------------------


def build_vertical(
    vert_key: str,
    spec: dict | list | set,
    *,
    pkg: str,
    registry: dict[str, object],
    edges_all: dict,
    templates_dir: Path,
    out_dir: Path,
    metainfo_base: str,
    feedback_url_base: str,
):
    # Normalize spec (support dict or bare list/set)
    if isinstance(spec, dict):
        title = spec.get('title', vert_key.title())
        sections = list(spec.get('sections', []))
        purpose = spec.get('purpose', '')
        in_scope = [clean_scope_item(item) for item in spec.get('in_scope', [])]
        out_of_scope = [clean_scope_item(item) for item in spec.get('out_of_scope', [])]
    else:
        title = vert_key.title()
        sections = list(spec)
        purpose, in_scope, out_of_scope = '', [], []

    # Diagram (already fenced and with blank lines)
    mermaid_block = mermaid_for_vertical(
        title, sections, edges_all, vert_key=vert_key, verticals_dict=VERTICALS
    )

    # Collect section info with quantities
    section_classes = resolve_section_classes(sections, registry)
    section_info = []
    for cls in section_classes:
        # Extract docstring for section description
        docstring = (cls.__doc__ or '').strip()
        # Get first complete sentence (up to first period followed by space or newline)
        brief = ''
        if docstring:
            # Join lines and split by sentence boundaries
            text = ' '.join(
                line.strip() for line in docstring.split('\n') if line.strip()
            )
            # Find first sentence ending
            import re

            match = re.match(r'^(.*?\.)\s', text)
            if match:
                brief = match.group(1)
            else:
                # If no clear sentence boundary, take first 150 chars
                brief = text[:150]
                if len(text) > 150:
                    brief += '...'
                elif brief and not brief.endswith('.'):
                    brief += '.'

        # Build full MetaInfo URL for this specific section
        # Format: {base}/{package}/section_definitions@{module_path}.{ClassName}
        module = cls.__module__
        class_name = cls.__name__
        metainfo_url = (
            f'{metainfo_base}/{pkg}/section_definitions@{module}.{class_name}'
        )

        # Collect quantities information for this section
        quantities = collect_quantities_info(cls)

        section_info.append(
            {
                'name': cls.__name__,
                'description': brief,
                'metainfo_url': metainfo_url,
                'quantities': quantities,
            }
        )

    # Render template
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(enabled_extensions=('html',)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tpl = env.get_template('vertical.md.j2')
    page_md = tpl.render(
        key=vert_key,
        title=title,
        purpose=purpose,
        in_scope=in_scope,
        out_of_scope=out_of_scope,
        sections=sections,
        section_info=section_info,
        metainfo_base=metainfo_base,
        mermaid_block=mermaid_block,  # already fenced
        feedback_url=f'{feedback_url_base}&labels=schema-review,vertical:{vert_key}'
        f'&title=[Review]%20{vert_key}',
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f'{vert_key}.md'
    out_file.write_text(page_md, encoding='utf-8')
    print(f'[gen_docs] Wrote {out_file}')


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description='Generate MkDocs pages for schema verticals.'
    )
    p.add_argument(
        '--pkg',
        default='nomad_simulations',
        help='Root package to introspect for MSection classes.',
    )
    p.add_argument(
        '--module-prefix',
        default='nomad_simulations',
        help='Filter edges to classes under this module prefix.',
    )
    p.add_argument(
        '--templates-dir',
        default='templates',
        help='Directory containing vertical.md.j2',
    )
    p.add_argument(
        '--out-dir',
        default='docs/schema',
        help='Output directory for generated Markdown pages.',
    )
    p.add_argument(
        '--metainfo-base',
        default='https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo',
        help='Base URL for the MetaInfo browser deeplinks.',
    )
    p.add_argument(
        '--feedback-url',
        default='https://github.com/nomad-coe/nomad-simulations/issues/new?template=schema-review.yml',
        help='Base URL for the GitHub Issue template.',
    )
    p.add_argument(
        '--search-mod',
        action='append',
        default=[],
        help='(Optional) Extra modules to scan for MSection classes.',
    )
    return p.parse_args(argv)


def build_index_page(
    verticals: dict,
    templates_dir: Path,
    out_dir: Path,
):
    """Generate the index.md overview page with links to all verticals."""
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(enabled_extensions=('html',)),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Prepare vertical data for template
    vert_list = []
    for key, spec in verticals.items():
        if isinstance(spec, dict):
            vert_list.append(
                {
                    'key': key,
                    'title': spec.get('title', key.title()),
                    'purpose': spec.get('purpose', ''),
                    'in_scope': spec.get('in_scope', []),
                    'sections': spec.get('sections', []),
                }
            )
        else:
            vert_list.append(
                {
                    'key': key,
                    'title': key.title(),
                    'purpose': '',
                    'in_scope': [],
                    'sections': list(spec),
                }
            )

    tpl = env.get_template('index.md.j2')
    page_md = tpl.render(verticals=vert_list)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'index.md'
    out_file.write_text(page_md, encoding='utf-8')
    print(f'[gen_docs] Wrote {out_file}')


def main(argv=None):
    args = parse_args(argv)

    registry = build_registry(args.pkg, args.search_mod)
    edges = collect_edges(pkg=args.pkg, only_modules_prefix=args.module_prefix)

    templates_dir = Path(args.templates_dir)
    out_dir = Path(args.out_dir)

    # Generate individual vertical pages
    for key, spec in VERTICALS.items():
        build_vertical(
            key,
            spec,
            pkg=args.pkg,
            registry=registry,
            edges_all=edges,
            templates_dir=templates_dir,
            out_dir=out_dir,
            metainfo_base=args.metainfo_base,
            feedback_url_base=args.feedback_url,
        )

    # Generate index page
    build_index_page(VERTICALS, templates_dir, out_dir)


if __name__ == '__main__':
    sys.exit(main())
