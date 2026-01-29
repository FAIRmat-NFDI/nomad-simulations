# Documentation Generation Pipeline

## Overview

This directory contains an automated pipeline for generating comprehensive schema documentation for the NOMAD-Simulations package. The system generates structured documentation pages with interactive Mermaid diagrams showing class relationships, organized into thematic "verticals" that cut through the schema hierarchy.

## Quick Start

Generate all documentation:
```bash
uv run python scripts/generate_docs_pipeline.py
```

This runs the complete pipeline:
1. Cleans old generated files
2. Generates Mermaid diagrams
3. Generates documentation pages
4. Converts diagrams to PNG/SVG
5. Updates navigation
6. Validates output

## Architecture

### Core Concepts

**Verticals**: Thematic "slices" through the schema that group related classes together. Each vertical represents a documentation page focusing on a specific aspect of the simulation schema (e.g., "Model System", "Electronic Properties", "Atomic State Properties").

**Filtering**: Intelligent edge filtering that shows/hides connections based on design rules to keep diagrams clean and focused at each hierarchical level.

**Auto-generation**: Everything is generated from the Python schema classes via introspection - no manual diagram maintenance.

### Key Files

| File | Purpose |
|------|---------|
| `generate_docs_pipeline.py` | Main orchestrator - runs all steps in sequence |
| `verticals.py` | **Source of truth** - defines all documentation verticals |
| `gen_diagrams.py` | Generates standalone `.diagram.md` files with Mermaid diagrams |
| `gen_docs.py` | Generates main schema pages (`.md`) from templates |
| `meta_introspect.py` | Introspects schema to collect edges (contain, refs, inherit) |
| `mermaid_to_svg.py` | Converts Mermaid to SVG for better rendering |
| `templates/vertical.md.j2` | Jinja2 template for documentation pages |

## The Verticals System

### What is a Vertical?

A vertical is a curated documentation page that focuses on a specific domain or level of the schema hierarchy. Think of it as a "horizontal cut" through a tree structure - it shows all classes at a similar conceptual level and their relationships.

### Design Principles

1. **Hierarchical Organization**: Verticals follow the natural schema hierarchy
   - `simulation` - Root entry point (Simulation, BaseSimulation, Program)
   - `model_system` - Physical system definition (ModelSystem, Cell, AtomicCell, etc.)
   - `atoms_state` - Detailed atomic properties (AtomsState → OrbitalsState, CoreHole, etc.)
   - `model_method` - Computational methods (DFT, GW, BSE, etc.)
   - `outputs` - Output properties and results

2. **Parent-Child Separation**: 
   - Parent pages show their direct children
   - Child pages show their internal structure
   - No redundant upward connections (child → parent)

3. **Inheritance Visibility**:
   - Inheritance arrows (`<|--`) always shown when relevant
   - Subclass implementation details hidden on parent pages
   - Full details visible on dedicated subclass pages

### Vertical Definition Structure

Each vertical in `verticals.py` includes:

```python
'vertical_key': {
    'title': 'Display Title',
    'purpose': 'One-line purpose statement',
    'sections': [
        'ClassName1',  # Classes to include in this vertical
        'ClassName2',
    ],
    'in_scope': [
        'Brief description of what is included',
    ],
    'out_of_scope': [
        'What is NOT included (with references to other verticals)',
    ],
}
```

## Diagram Filtering Logic

### The Problem

Without filtering, diagrams become cluttered:
- ModelSystem page shows redundant connection back to Simulation
- Child class diagrams show all parent connections
- Implementation details leak into high-level overviews

### The Solution: Smart Edge Filtering

Implemented in `gen_diagrams.py::filter_edges_for_vertical()`:

```python
def filter_edges_for_vertical(vert_key, allowlist, all_edges, verticals_dict):
    """
    Design Rules:
    1. Parent sections (Simulation, ModelSystem, etc.) SHOW all their direct children
    2. Non-parent sections DON'T show connections to parent sections
    3. Classes with their own pages don't show their subsections on other pages
    """
```

#### Filtering Rules

1. **Parent → Child (SHOW)**
   - If source is a parent section (Simulation, ModelSystem, ModelMethod, Outputs)
   - AND source is in this vertical's allowlist
   - THEN show all its direct children (even if they have their own pages)

2. **Child → Parent (HIDE)**
   - If target is a parent section
   - AND target is NOT in this vertical's allowlist
   - THEN hide the connection (redundant with parent page)

3. **Subsection Detail (CONTEXT-DEPENDENT)**
   - If target has its own vertical/page
   - AND target is NOT in current allowlist
   - THEN hide its subsections (they're shown on the target's own page)

### Example: ModelSystem Vertical

```
Simulation Entry Page:
  Simulation → ModelSystem  ✓ (parent showing child)
  Simulation → ModelMethod  ✓
  Simulation → Outputs      ✓

ModelSystem Page:
  Simulation → ModelSystem  ✗ (child hiding parent - redundant)
  ModelSystem → Cell        ✓ (showing direct children)
  ModelSystem → AtomsState  ✓
  Cell <|-- AtomicCell      ✓ (inheritance always shown)
  
AtomsState Page:
  ModelSystem → AtomsState  ✗ (child hiding parent)
  AtomsState → OrbitalsState ✓ (showing subsections)
  AtomsState → CoreHole      ✓
```

## Pipeline Steps Explained

### 1. Cleanup (`clean_old_docs()`)

Removes only generated files to prevent stale content:
- Matches filenames against `VERTICALS` keys
- Deletes corresponding `.md` and `.diagram.md` files
- Leaves manually created files untouched

### 2. Diagram Generation (`gen_diagrams.py`)

For each vertical:
1. Collects all edges (contain, refs, inherit) via `meta_introspect`
2. Applies filtering rules via `filter_edges_for_vertical()`
3. Finds connected components
4. Categorizes nodes (root connectors, inheritance trees)
5. Generates Mermaid classDiagram syntax
6. Adds visual legend with SVG arrows
7. Writes standalone `.diagram.md` file

### 3. Documentation Generation (`gen_docs.py`)

For each vertical:
1. Loads Jinja2 template (`vertical.md.j2`)
2. Generates filtered Mermaid diagram (embedded in page)
3. Collects section classes from registry
4. Generates micro-examples (YAML format)
5. Builds MetaInfo URLs
6. Renders template with all context
7. Writes `.md` file to `docs/schema/`

### 4. Mermaid Conversion

Two options:
- **SVG** (current): `mermaid_to_svg.py` - uses Chrome headless shell via Puppeteer
- **PNG** (legacy): `mermaid_to_png.py` - uses mermaid-cli

SVG benefits:
- Better quality at all zoom levels
- Smaller file sizes
- Clickable elements
- Color preservation

### 5. Navigation Update

Generates:
- `mkdocs.yml`: Main navigation structure
- `docs/schema/.pages`: Awesome-pages plugin config

Auto-syncs navigation with verticals defined in `verticals.py`.

### 6. Validation

Checks:
- All vertical keys appear in navigation
- No extra/missing entries
- File structure matches expectations

## Edge Types

Three types of relationships are tracked:

1. **Containment** (`-->` solid arrow)
   - SubSection relationships
   - Example: `ModelSystem --> Cell`
   - Represents "has-a" relationships

2. **Reference** (`..>` dashed arrow)
   - Quantity type references
   - Example: `Output ..> ModelSystem`
   - Represents "uses" or "points-to" relationships

3. **Inheritance** (`<|--` open triangle arrow)
   - Class inheritance
   - Example: `Cell <|-- AtomicCell`
   - Represents "is-a" relationships

## Visual Design

### Mermaid Diagram Features

- **Component Separation**: Disconnected subgraphs shown with `---` separator
- **Priority Sorting**: Root-connected components appear first
- **Normalized Labels**: Redundant edge labels removed (e.g., "cells" → Cell just shows arrow)
- **Clean Styling**: Empty class boxes (no UML dividers)

### SVG Arrow Legend

Each diagram includes an inline SVG legend:

```html
<svg width="60" height="30">
  <line/><polygon fill="none"/> <!-- Inheritance: open triangle -->
  <line/><polygon fill="currentColor"/> <!-- Containment: filled triangle -->
  <line stroke-dasharray="4,4"/><polygon/> <!-- Reference: dashed + filled -->
</svg>
```

## Adding a New Vertical

1. **Define in `verticals.py`**:
   ```python
   'my_new_vertical': {
       'title': 'My New Vertical',
       'purpose': 'Brief description',
       'sections': ['ClassName1', 'ClassName2'],
       'in_scope': ['What is included'],
       'out_of_scope': ['What is not (see other_vertical)'],
   }
   ```

2. **Run pipeline**:
   ```bash
   uv run python scripts/generate_docs_pipeline.py
   ```

3. **Verify output**:
   - Check `docs/schema/my_new_vertical.md`
   - Check `docs/schema/my_new_vertical.diagram.md`
   - Verify navigation updated automatically

## Troubleshooting

### Diagrams Too Complex

Reduce the `sections` list in the vertical - split into multiple focused verticals.

### Missing Connections

Check if classes are in the vertical's `allowlist`. The filtering logic only shows edges where at least one endpoint is in the allowlist.

### Redundant Parent Connections

Ensure parent sections (`Simulation`, `ModelSystem`, etc.) are listed in the `parent_sections` set in `filter_edges_for_vertical()`.

### Chrome/Puppeteer Issues

SVG conversion requires Chrome headless shell. If missing:
```bash
npx @puppeteer/browsers install chrome-headless-shell@131.0.6778.204
```

Or fall back to PNG:
```bash
npx -p @mermaid-js/mermaid-cli mmdc -i input.md -o output.png
```

## File Organization

```
scripts/
├── README.md                    # This file
├── verticals.py                 # Source of truth for documentation structure
├── generate_docs_pipeline.py    # Main orchestrator
├── gen_diagrams.py              # Mermaid diagram generation
├── gen_docs.py                  # Documentation page generation
├── meta_introspect.py           # Schema introspection
├── mermaid_to_svg.py            # SVG conversion (current)
├── mermaid_to_png.py            # PNG conversion (legacy)
└── templates/
    └── vertical.md.j2           # Page template

docs/schema/
├── simulation.md                # Generated page
├── simulation.diagram.md        # Generated standalone diagram
├── model_system.md              # ...
└── assets/diagrams/
    ├── simulation_0.svg         # Converted diagram
    └── model_system_0.svg       # ...
```

## Design History

### Evolution of Filtering Logic

**v1**: No filtering - cluttered diagrams with all possible connections

**v2**: Basic allowlist filtering - only show nodes in vertical

**v3**: Parent exclusion - hide connections to parent sections

**v4** (current): Smart hierarchical filtering
- Parent pages show children
- Child pages hide parents  
- Subsection details contextual
- Inheritance always visible

### Why Verticals?

Alternative approaches considered:
1. **One page per class**: Too fragmented, hard to see big picture
2. **One page total**: Too overwhelming, no focused views
3. **Auto-generated hierarchy**: Misses conceptual groupings
4. **Verticals** ✓: Balance between focus and context

## Performance

Typical full regeneration: ~5-10 seconds

Breakdown:
- Introspection: ~1s
- Diagram generation: ~1s  
- Doc generation: ~1s
- SVG conversion: ~2-6s (depends on diagram count)
- Navigation update: <1s

## Future Enhancements

- [ ] Interactive filtering in web UI
- [ ] Collapsible diagram sections
- [ ] Cross-vertical search
- [ ] Auto-detect concrete vs abstract classes
- [ ] Custom diagram themes
- [ ] Incremental regeneration

## References

- [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)
- [Mermaid Class Diagrams](https://mermaid.js.org/syntax/classDiagram.html)
- [Jinja2 Templates](https://jinja.palletsprojects.com/)
- [NOMAD MetaInfo](https://nomad-lab.eu/prod/v1/docs/reference/metainfo.html)

## Contributing

When modifying the pipeline:

1. **Test thoroughly**: Run full pipeline and verify all pages
2. **Update verticals.py**: Keep it as single source of truth
3. **Document design decisions**: Update this README
4. **Maintain filtering logic**: Don't break hierarchical principles
5. **Check navigation**: Ensure automatic updates still work

## License

Same as nomad-simulations parent package.
