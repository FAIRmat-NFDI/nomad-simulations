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
5. Configures diagram zoom method (panzoom or simple)
6. Updates navigation (including hierarchical structure)
7. Validates output

## Diagram Zoom Configuration

The pipeline supports two methods for diagram interaction:

- **`panzoom`** (default): Advanced scroll-wheel zoom + drag pan using `mkdocs-panzoom-plugin`
- **`simple`**: Basic click-to-zoom using custom JavaScript

To switch between methods, edit `generate_docs_pipeline.py`:

```python
# Around line 28
DIAGRAM_ZOOM_METHOD = 'panzoom'  # or 'simple'
```

See [DIAGRAM_ZOOM.md](DIAGRAM_ZOOM.md) for detailed configuration guide.

## Switching Between Diagram Modes

You can control whether the pipeline generates PNG/SVG images or just uses fast Mermaid diagrams with pan/zoom by setting the `DIAGRAM_ZOOM_METHOD` variable at the top of `scripts/generate_docs_pipeline.py`:

- **Fast Mermaid diagrams with pan/zoom (recommended for large docs):**
  ```python
  DIAGRAM_ZOOM_METHOD = 'panzoom'
  ```
  - No PNG/SVG images are generated (pipeline is much faster)
  - Diagrams are rendered as Mermaid code blocks in Markdown
  - Pan/zoom is enabled via the mkdocs-panzoom-plugin

- **Classic image-based docs (PNG/SVG, click-to-zoom):**
  ```python
  DIAGRAM_ZOOM_METHOD = 'simple'
  ```
  - Pipeline generates PNG and SVG images for all diagrams (slower)
  - Diagrams are embedded as images in the docs
  - Click-to-zoom is enabled via custom JavaScript

**How to switch:**
1. Edit `scripts/generate_docs_pipeline.py` and set `DIAGRAM_ZOOM_METHOD` as above.
2. Run the pipeline:
   ```bash
   uv run python scripts/generate_docs_pipeline.py
   ```
3. Serve your docs:
   ```bash
   uv run mkdocs serve
   ```

The pipeline will automatically handle all configuration and file generation for the selected mode. The summary output will indicate which files were generated and which zoom method is active.

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
| `DIAGRAM_ZOOM.md` | Guide for configuring diagram zoom/pan methods |

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
### Design Principles

1. **Inheritance-Based Organization**:
   - Each vertical represents ONE inheritance hierarchy
   - Parent class and ALL child classes on the same page
   - Child classes' subsections also included on the same page
   - Example: `particle_state` contains ParticleState → AtomsState (with OrbitalsState, CoreHole, HubbardInteractions) + CGBeadState

2. **Complete Hierarchy Per Page**:
   - Include parent class
   - Include all direct child classes (via inheritance)
   - Include all subsections of those child classes
   - Do NOT split inheritance families across multiple pages

3. **Top-Level Entry Points**:
   - `simulation` - Root Simulation entry (references other top-level sections)
   - `model_system` - Root ModelSystem (references Cell, ParticleState, etc.)
   - Other top-level pages just reference their subsections

4. **No Redundant Upward Connections**:
   - Child pages don't show connections back to parents
   - Subsection pages don't show connections to containing classes from other verticals

5. **Inheritance Visibility**:
   - Inheritance arrows (`<|--`) always shown when both classes in allowlist
   - Shows complete class hierarchy on one page

### Vertical Definition Structure

Each vertical in `verticals.py` includes:

```python
'vertical_key': {
    'title': 'Display Title',
    'purpose': 'One-line purpose statement',
    'sections': [
        'ParentClass',      # Base class of inheritance hierarchy
        'ChildClass1',      # Direct child via inheritance
        'ChildClass2',      # Another child
        'SubSection1',      # Subsection of ChildClass1
        'SubSection2',      # Another subsection of ChildClass1
    ],
    'in_scope': [
        'ParentClass: description',
        'ChildClass1: description with subsections SubSection1, SubSection2',
        'ChildClass2: description',
    ],
    'out_of_scope': [
        'What is NOT included (with references to other verticals)',
    ],
}
```

### Organization Examples

**Good** ✓ Complete inheritance hierarchy on one page:
```python
'particle_state': {
    'sections': [
        'ParticleState',        # Parent
        'AtomsState',           # Child 1
        'CGBeadState',          # Child 2
        'OrbitalsState',        # Subsection of AtomsState
        'CoreHole',             # Subsection of AtomsState
        'HubbardInteractions',  # Subsection of AtomsState
    ],
}
```

**Bad** ✗ Splitting subsections to separate page:
```python
'particle_state': {
    'sections': ['ParticleState', 'AtomsState', 'CGBeadState'],
}
'atomic_properties': {  # DON'T DO THIS
    'sections': ['OrbitalsState', 'CoreHole', 'HubbardInteractions'],
}
```

## Diagram Filtering Logic

### The Problem

Without filtering, diagrams become cluttered:
- ModelSystem page shows redundant connection back to Simulation
- Child class diagrams show all parent connections
- Implementation details leak into high-level overviews
- Pages with many children create very wide, hard-to-read diagrams

### The Solution: Smart Edge Filtering + Diagram Partitioning

Implemented in `gen_diagrams.py::filter_edges_for_vertical()` and `partition_children_for_diagrams()`:

```python
def filter_edges_for_vertical(vert_key, allowlist, all_edges, verticals_dict):
    """
    Design Rules:
    1. Parent sections SHOW all their direct children
    2. Non-parent sections DON'T show connections to parent sections
    3. Classes with their own pages don't show their subsections on other pages
    4. Inheritance always shown if both classes in allowlist
    """

def partition_children_for_diagrams(parent_nodes, all_children, filtered_edges):
    """
    When a parent has >12 children, split into multiple diagrams:
    - Keep connected children together
    - Show parent(s) in each diagram
    - Stack diagrams vertically on the same page
    """
```

#### Filtering Rules

1. **Parent → Child (ALWAYS SHOW)**
   - If source is a parent section (Simulation, ModelSystem, ModelMethod, Outputs)
   - AND source is in this vertical's allowlist
   - THEN show ALL its direct children
   - Maintains complete visibility of parent-child relationships

2. **Child → Parent (HIDE)**
   - If target is a parent section
   - AND target is NOT in this vertical's allowlist
   - THEN hide the connection (redundant with parent page)

3. **Subsection Detail (CONTEXT-DEPENDENT)**
   - If target has its own vertical/page
   - AND target is NOT in current allowlist
   - THEN hide its subsections (they're shown on the target's own page)

4. **Inheritance (ALWAYS SHOW)**
   - If both parent and child are in the allowlist
   - THEN always show inheritance edges
   - Inheritance structure is fundamental to understanding the schema

#### Diagram Partitioning Rules

When a parent class has many children (>12), the diagram is automatically split:

1. **Multiple Diagrams on Same Page**
   - Split children into groups of ≤12 per diagram
   - Show parent node in each diagram
   - Stack diagrams vertically with separators

2. **Keep Connected Children Together**
   - If children have edges between them (containment, reference, or inheritance)
   - Keep them in the same diagram
   - Use DFS to find connected components among children

3. **Balanced Partitioning**
   - Find connected groups of children
   - Pack groups into diagrams to balance size
   - Prefer diagrams with similar numbers of children

4. **Visual Clarity**
   - Each sub-diagram labeled "Diagram X of Y"
   - Horizontal separator (---) between diagrams
   - Single legend after final diagram

### Example: ModelSystem Vertical

```
Simulation Entry Page:
  Simulation → ModelSystem  ✓ (parent showing child)
  Simulation → ModelMethod  ✓
  Simulation → Outputs      ✓

ModelSystem Page (if many children, split into diagrams):
  Diagram 1:
    ModelSystem → Cell        ✓
    ModelSystem → AtomicCell  ✓
    ModelSystem → Symmetry    ✓
    ... (up to 12 children)

  Diagram 2:
    ModelSystem → ParticleState  ✓
    ModelSystem → ChemicalFormula ✓
    ... (remaining children)

  (Simulation → ModelSystem NOT shown - child hiding parent)

Cell Page:
  ModelSystem → Cell  ✗ (child hiding parent)
  Cell <|-- AtomicCell      ✓ (inheritance always shown)
```

### Example: Outputs with Many Properties

```
Outputs Base Page (20+ children → split into diagrams):
  Diagram 1 (Electronic properties group):
    Outputs → BaseElectronicEigenvalues  ✓
    Outputs → ElectronicEigenvalues      ✓
    BaseElectronicEigenvalues <|-- ElectronicEigenvalues  ✓
    ElectronicEigenvalues <|-- ElectronicBandStructure    ✓
    ... (connected children kept together)

  Diagram 2 (Energy properties group):
    Outputs → BaseEnergy    ✓
    Outputs → TotalEnergy   ✓
    BaseEnergy <|-- TotalEnergy  ✓
    ... (another group of children)

  (All parent-child relationships preserved, just split across diagrams)
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

Automatically updates:
- `docs/schema/.pages`: Awesome-pages plugin config (list of all vertical .md files)
- `mkdocs.yml`: Main navigation structure (Schema Navigation section with titles)

The pipeline uses regex to find and replace the "Schema Navigation:" section in `mkdocs.yml`, automatically syncing it with all verticals defined in `verticals.py`. Each vertical's title is used in the navigation menu.

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

## Updating Verticals When Schema Changes

The verticals in `verticals.py` are the **single source of truth** for documentation organization. When the schema changes (new classes, renamed classes, refactored hierarchies), you must manually update the verticals. The pipeline does NOT automatically detect schema changes.

### When to Update Verticals

Update `verticals.py` when:

1. **New schema classes are added**
   - Add class names to appropriate vertical's `sections` list
   - Follow inheritance-based organization (parent + children on same page)

2. **Classes are renamed**
   - Update class names in all affected `sections` lists
   - Update cross-references in `in_scope` and `out_of_scope`

3. **Inheritance hierarchy changes**
   - Reorganize verticals to group parent/child classes together
   - Example: If `Cell` gains a new subclass, add it to the `cell` vertical

4. **New subsections added to existing classes**
   - If subsection has its own inheritance tree, create new vertical
   - If subsection is a simple container, add to parent's vertical

5. **Classes moved between modules**
   - No update needed - introspection handles module paths automatically

### Organization Principles

**Rule 1: Inheritance Families Together**
- Parent class and all direct children on the same page
- Example: `cell` vertical contains `GeometricSpace`, `Cell`, `AtomicCell`

**Rule 2: Subsection Details Separate**
- Classes that are contained WITHIN others get their own vertical
- Example: `atoms_state` shows `AtomsState → OrbitalsState, CoreHole, HubbardInteractions`

**Rule 3: One Responsibility Per Page**
- Each vertical should focus on one concept/hierarchy level
- Don't mix unrelated classes just to reduce page count

### Update Workflow

1. **Identify schema changes**:
   ```bash
   # Check what classes exist in the schema
   uv run python -c "
   from nomad_simulations.schema_packages import model_system, atoms_state, model_method
   for module in [model_system, atoms_state, model_method]:
       print(f'\n{module.__name__}:')
       for name in dir(module):
           obj = getattr(module, name)
           if hasattr(obj, 'm_def') and hasattr(obj.m_def, 'name'):
               print(f'  - {name}')
   "
   ```

2. **Update `verticals.py`**:
   - Add new classes to `sections` lists
   - Update `purpose`, `in_scope`, `out_of_scope` descriptions
   - Maintain alphabetical order within sections (optional but helpful)

3. **Run pipeline**:
   ```bash
   uv run python scripts/generate_docs_pipeline.py
   ```

4. **Review generated docs**:
   - Check diagrams show expected relationships
   - Verify no missing classes (pipeline doesn't warn about this)
   - Ensure cross-references in `out_of_scope` are still valid

### Example: Adding a New Class

Scenario: New class `PeriodicCell` added that inherits from `Cell`.

**Before:**
```python
'cell': {
    'sections': [
        'GeometricSpace',
        'Cell',
        'AtomicCell',
    ],
}
```

**After:**
```python
'cell': {
    'sections': [
        'GeometricSpace',
        'Cell',
        'AtomicCell',
        'PeriodicCell',  # New class added
    ],
    'in_scope': [
        'GeometricSpace: base section for defining geometrical spaces',
        'Cell: cell quantities and lattice vectors',
        'AtomicCell: atomic cell information extending Cell',
        'PeriodicCell: periodic cell with explicit periodicity flags',  # New description
        # ... rest
    ],
}
```

### Example: Refactoring Hierarchy

Scenario: `ModelMethod` hierarchy reorganized - `DFT` split into `KSDFT` and `OFDFT`.

**Before:**
```python
'model_method': {
    'sections': [
        'ModelMethod',
        'ModelMethodElectronic',
        'DFT',
        'XCFunctional',
    ],
}
```

**After:**
```python
'model_method': {
    'sections': [
        'ModelMethod',
        'ModelMethodElectronic',
        'DFT',
        'KSDFT',          # New: Kohn-Sham DFT
        'OFDFT',          # New: Orbital-Free DFT
        'XCFunctional',
    ],
}
```

### Common Mistakes

❌ **Don't**: Split inheritance hierarchies across multiple verticals
- All parent + children + their subsections must be on ONE page
- Example: Don't create separate pages for AtomsState and OrbitalsState

❌ **Don't**: Forget to include subsections of child classes
- If AtomsState has OrbitalsState, CoreHole subsections, include them all in particle_state vertical

❌ **Don't**: Forget to remove deleted classes
- Old class names will cause pipeline errors

❌ **Don't**: Mix unrelated inheritance hierarchies on one page
- Keep `Cell` family separate from `ParticleState` family

❌ **Don't**: Create too many small verticals
- Balance between focused pages and navigation complexity

✅ **Do**: Keep complete inheritance families together (parent + all children + all subsections)

✅ **Do**: Document purpose clearly in `purpose` field

✅ **Do**: Maintain cross-references in `out_of_scope`

✅ **Do**: List all subsections of child classes in the `sections` list

### Validation Checklist

After updating verticals, verify:

- [ ] All class names in `sections` exist in schema (no typos)
- [ ] Inheritance families are complete (parent + all children + subsections of children)
- [ ] No inheritance hierarchy is split across multiple verticals
- [ ] Cross-references in `out_of_scope` point to existing verticals
- [ ] `purpose` field accurately describes page content
- [ ] Diagrams render correctly without errors
- [ ] Navigation structure makes sense

## Managing Diagram Complexity

### The Problem: Huge Diagrams

Some inheritance hierarchies (especially outputs and properties) can have 20+ classes with complex interconnections, leading to:
- Overwhelming visual complexity
- Slow diagram rendering
- Poor readability
- Difficult navigation

### Design Rules for Complex Hierarchies

**Rule 1: Split by Domain/Purpose**
- Instead of one massive "outputs" page with 50+ classes
- Create focused domain pages: electronic_properties, thermodynamics, spectroscopy, etc.
- Each page should cover 5-15 classes maximum

**Rule 2: Hierarchical Layering**
- Top-level page: Base classes only (Outputs, PhysicalProperty)
- Second-level pages: Specialized domains (ElectronicEigenvalues, BaseEnergy, SpectralProfile)
- Keep inheritance depth ≤ 3 levels on a single diagram

**Rule 3: Cross-Reference, Don't Duplicate**
- Use `out_of_scope` to point to related verticals
- Example: "Electronic structure properties (see electronic_properties)"
- Don't show all possible connections - focus on the current domain

**Rule 4: Hide Implementation Details**
- Abstract base classes on top-level pages
- Concrete implementations on specialized pages
- Example: `BaseElectronicEigenvalues` on outputs page, `ElectronicBandStructure` on electronic_properties page

### Example: Outputs Hierarchy Split

**Bad** ✗ One huge diagram:
```python
'outputs': {
    'sections': [
        'Outputs', 'SCFOutputs', 'PhysicalProperty',
        'BaseElectronicEigenvalues', 'ElectronicEigenvalues', 'ElectronicBandStructure',
        'ElectronicBandGap', 'DOSProfile', 'ElectronicDensityOfStates',
        'BaseEnergy', 'TotalEnergy', 'KineticEnergy', 'PotentialEnergy',
        'BaseGreensFunction', 'ElectronicGreensFunction', 'ElectronicSelfEnergy',
        # ... 40+ more classes
    ],
}
```

**Good** ✓ Domain-focused verticals:
```python
'outputs': {
    'title': 'Outputs Base',
    'sections': ['Outputs', 'SCFOutputs', 'PhysicalProperty'],
    'out_of_scope': [
        'Electronic properties (see electronic_properties)',
        'Thermodynamics (see thermodynamics)',
        'Many-body properties (see manybody_properties)',
    ],
},
'electronic_properties': {
    'title': 'Electronic Structure Properties',
    'sections': [
        'BaseElectronicEigenvalues',
        'ElectronicEigenvalues',
        'ElectronicBandStructure',
        'ElectronicBandGap',
        'DOSProfile',
        'ElectronicDensityOfStates',
    ],
},
'thermodynamics': {
    'title': 'Thermodynamic Properties',
    'sections': [
        'BaseEnergy',
        'TotalEnergy',
        'KineticEnergy',
        'PotentialEnergy',
        # ... related energy classes only
    ],
},
```

### Diagram Size Guidelines

| Classes | Recommendation | Action |
|---------|---------------|--------|
| 1-5 | Perfect | Single vertical, simple diagram |
| 6-15 | Good | Single vertical, manageable diagram |
| 16-25 | Complex | Consider splitting by subdomain |
| 26+ | Too large | **Must split** into multiple verticals |

### When to Split a Vertical

Split when:
1. **Visual complexity**: Diagram is hard to read even with filtering
2. **Multiple domains**: Classes serve different conceptual purposes
3. **Deep hierarchies**: >3 levels of inheritance on one page
4. **Unrelated groups**: Classes that don't directly relate to each other

Don't split when:
1. **Tight coupling**: Classes frequently reference each other
2. **Shallow hierarchy**: All classes at same level
3. **Single purpose**: All classes serve one focused goal

### Refactoring Strategy

To refactor a large vertical:

1. **Identify natural groupings**:
   ```bash
   # Analyze the inheritance tree
   # Look for common base classes or functional domains
   ```

2. **Create new verticals for each group**:
   ```python
   'base_vertical': {
       'sections': ['BaseClass1', 'BaseClass2'],  # Abstract bases only
       'out_of_scope': ['Specializations (see specialized_vertical)'],
   },
   'specialized_vertical': {
       'sections': ['ConcreteClass1', 'ConcreteClass2', ...],
       'out_of_scope': ['Base definitions (see base_vertical)'],
   },
   ```

3. **Update cross-references** in all affected `out_of_scope` lists

4. **Test rendering**: Verify each diagram is readable

### Filtering Enhancements for Large Diagrams

The filtering logic already helps by:
- Hiding parent connections from child pages
- Excluding subsections when target has own page
- Showing only allowlisted connections

For very large hierarchies, consider:
- Keeping only inheritance edges (`<|--`) on base pages
- Moving containment edges (`-->`) to specialized pages
- Minimizing reference edges (`..>`) to reduce clutter

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
