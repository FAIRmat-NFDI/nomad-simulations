# `ModelSystem`

!!! warning
    This page is still under construction.

## Overview

The `ModelSystem` section represents a model of a physical system, both in

- structure, e.g. (atomic) positions, lattice parameters, and symmetry
- and composition, e.g. elements and their computational settings, coarse-graining.

## Key Design Principle: One System, Multiple Representations

A fundamental design principle of `ModelSystem` is that **there is exactly one `ModelSystem` per physical system**. Different structural representations (primitive, conventional, supercells, etc.) are handled through multiple `Cell` sections within the same `ModelSystem`, not by creating separate `ModelSystem` instances.

```python
model_system = ModelSystem()
# One physical system (e.g., silicon crystal)

# Multiple cells for different representations:
model_system.cell[0]  # Original/input cell
model_system.cell[1]  # Primitive cell  
model_system.cell[2]  # Conventional cell
```

<!-- @ndaelman-hu: am not completely sold on the placement of `cell`, as all the crystallographic examples tie in with `Symmetry` -->

  ## Subsystems and Hierarchical Organization

  `ModelSystem` supports **hierarchical subsystem organization** beyond just multiple cell representations. This enables modeling of complex multi-component systems like heterostructures, surfaces with adsorbates, or solutions, monomers within polymers, elemental distribution.
  These subsets do **not** have to form a partition.

  ### Key Concepts:
  - **Root system**: Contains all atomic positions and the complete structural data
  - **Subsystems**: Reference subsets of atoms via `particle_indices` without duplicating geometric data
  - **Hierarchical nesting**: Subsystems can contain their own subsystems (e.g., device → component → molecule)


All subsystems leverage previously registered geometric data by referring directly to the **top-level node**, i.e. the **complete system**.
This allows for single-access lookups rather than recursive traversals.

  ```python
  # Example: Heterostructure modeling
  heterostructure = ModelSystem(name='Si/GaAs', is_representative=True)
  heterostructure.positions = [...]  # All atomic positions

  # Subsystem 1: Silicon layer
  si_layer = ModelSystem(name='Si_layer', particle_indices=[0, 1, 2, 3])
  heterostructure.sub_systems.append(si_layer)

  # Subsystem 2: GaAs layer
  gaas_layer = ModelSystem(name='GaAs_layer', particle_indices=[4, 5, 6, 7, 8, 9])
  heterostructure.sub_systems.append(gaas_layer)
```


## Structure Representations via `Cell` Sections

### Cell Types and Their Purpose

1. **Original Cell** (`type='original'`)
   - The cell as provided in the input/calculation
   - May be any arbitrary choice of unit cell
   - Contains the lattice vectors used in the actual computation

2. **Primitive Cell** (`type='primitive'`)  
   - Smallest possible unit cell that tiles the crystal
   - Contains minimum number of lattice points
   - Used for certain calculations (e.g., band structures)

3. **Conventional Cell** (`type='conventional'`)
   - Standardized cell following International Tables conventions
   - Used for symmetry analysis and crystallographic databases
   - **Typically used to define symmetry operators:** ["x,y,z", "-x,y,-z", "x+1/2,y+1/2,z", "-x+1/2,y+1/2,-z"] (conventional) vs ["x,y,z", "-x,-y,z", "-x,y,-z", "x,-y,-z"] (primitive).
  
<!-- @ndaelman-hu: This is one reading, where we use primitive and conventional to define different symmetry representations.
The alternative would be to simply label the parsed cell. -->

!!! note Crystal symmetry specification
    Crystal symmetry operators are dependent on various factors.
    International table adopt **conventional cell settings** for identify space group operations.
    These are also used for indexing the space group, which tends to be less situation-dependent.
     - The same crystal structure gives **different coordinate operations** depending on cell choice
     - Origin placement and axis orientation affect the algebraic form of operations
     - Database interoperability requires standardized representations

## Particle Positions: An Open Question

Currently, `ModelSystem` stores particle positions at the top level (`ModelSystem.positions`), but these positions correspond to only **one** of the multiple cell representations. This creates ambiguity about which cell the positions refer to.

```python
model_system = ModelSystem()
model_system.positions = [[0.0, 0.0, 0.0], [0.25, 0.25, 0.25]]  # Which cell?
model_system.cell[0] = Cell(type='original', lattice_vectors=...)    # These positions?
model_system.cell[1] = Cell(type='primitive', lattice_vectors=...)   # Or these positions?
model_system.cell[2] = Cell(type='conventional', lattice_vectors=...) # Or these positions?
```

## Coordinate Systems and Symmetry Descriptions

The `Cell` section **defines the coordinate system** (origin and orientation) for the structural representation.
This is especially relevant for codes that allow adjustments of the simulation box, which may potentially affect the coordinates.
All atomic positions (`ModelSystem.positions`) are interpreted **relative to the active cell's coordinate system**. The same fractional coordinates have different Cartesian meanings in different cells:

```python
# Same fractional coordinate [0.25, 0.25, 0.25] in different cells:
primitive_cell:     # → Cartesian [1.35, 1.35, 1.35] Å  
conventional_cell:  # → Cartesian [1.35, 1.35, 1.35] Å (same in this case)
supercell:         # → Cartesian [2.7, 2.7, 2.7] Å (different!)
```

Subsystems may have different, more appropriate coordinate systems, in which case they contain their own `ModelSystem.cell`.

When applicable, `Cell` also defines boundary conditions and periodicity; the unit cell and repeating tiles; as well as lattice parameters.

### `Symmetry`: System-Level Symmetry Description

The `Symmetry` section describes the **overall symmetry of the (sub)system**, not individual atomic sites:

```python
symmetry = Symmetry(
    space_group_number=227,              # System-level space group
    space_group_symbol='Fd-3m',         # Overall crystal symmetry
    point_group_symbol='m-3m',          # Point group of the system
    crystal_system='cubic',             # System belongs to cubic family
)
```

Its purpose is to provide as many search options as possible, including symmetry and prototype classifications.
To this end, it may also list all symmetry operators and even enumerate their different representations. <!-- @ndaelman-hu: This isn't currently used yet -->

### Individual Site Information: A Different Layer

**Neither `Cell` nor `Symmetry` describes individual atomic sites**. This information lives elsewhere:

```python
# Individual site symmetries are NOT in the Symmetry section
# They are derived properties or stored separately:

model_system.wyckoff_sites = ['a8']  # Site-specific Wyckoff assignments
# Each position has its own local site symmetry (e.g., '4mm', '3m', '1')
```

**Distinction:**
- **System symmetry** (in `Symmetry`): *"This crystal has space group Fd-3m"*
- **Site symmetry** (not in `Symmetry`): *"Atom 1 sits on a site with 4mm point symmetry"*
- **Coordinate system** (in `Cell`): *"Fractional coordinates are defined relative to these lattice vectors"*

### Integration Example: Silicon Crystal

```python
si_system = ModelSystem()

# CELL: Defines the coordinate framework
si_system.cell[0] = Cell(
    type='conventional',
    lattice_vectors=[[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]] * ureg.angstrom
    # → Establishes cubic coordinate system
)

# POSITIONS: Interpreted within the cell's coordinate system
si_system.positions = [
    [0.0, 0.0, 0.0],      # → (0,0,0) in cubic coordinates
    [0.25, 0.25, 0.25],   # → (1.36,1.36,1.36) Å in Cartesian
    [0.5, 0.5, 0.0],      # → (2.72,2.72,0) Å in Cartesian
    # ... 8 atoms total
] * ureg.angstrom

# SYMMETRY: Describes system-wide symmetry properties
si_system.symmetry[0] = Symmetry(
    space_group_number=227,        # System has Fd-3m symmetry
    point_group_symbol='m-3m',     # System point group
    crystal_system='cubic',        # System is cubic overall
    # NOT: individual site symmetries of the 8 atoms
)

# SITE-LEVEL INFO: Stored separately from system-level symmetry
si_system.wyckoff_sites = ['a8']  # All 8 atoms are on Wyckoff site 8a
# Each atom individually has site symmetry '-3m' (not stored in Symmetry section)
```

**Key insight:** The same `Symmetry` section describes the system regardless of which `Cell` representation is active, because the physical symmetry doesn't change - only the mathematical description of coordinates changes.

## Wyckoff Positions and Symmetry Context

### Wyckoff Site Annotations

`ModelSystem` provides Wyckoff site information through the `wyckoff_sites` quantity:

```python
model_system.wyckoff_sites = ['a4', 'b2', 'c1']  # Format: letter + multiplicity
```

**Key features:**
  - Format: <letter><multiplicity> (e.g., 'a1', 'b2')
  - Crystallographic standard: Based on International Tables for Crystallography
  - Geometric classification: Determined by atomic positions only (chemical species ignored)
  - Per-atom assignment: Each entry corresponds to the position at the same index

  Important: Wyckoff assignments are computed relative to the conventional cell representation, ensuring database compatibility and literature consistency.

  For complete structural uniqueness, combine Wyckoff information with chemical composition data.

## Related Sections

- [`Cell`](./cell.md) - Detailed cell representation and geometric parameters
- [`Symmetry`](./symmetry.md) - Space group information and crystallographic symmetry  
- [`AtomState`](./atom_state.md) - Individual atomic properties and states