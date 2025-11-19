# `ModelSystem`

## Overview

The `ModelSystem` class represents the physical system that serves as input for simulation calculations in NOMAD. It provides a comprehensive description of the atomic or coarse-grained structure, including particle positions, cell geometry, symmetry information, and chemical composition.

`ModelSystem` combines two fundamental capabilities: geometric representation (from the `Representation` class) and hierarchical navigation (from the `System` class). This means each model system has direct access to its geometric data (lattice vectors, atomic positions, periodic boundary conditions) while also supporting navigation through subsystem hierarchies and alternative geometric views.

A `ModelSystem` can represent various types of systems: bulk crystals, surfaces, molecules, clusters, or complex hierarchical structures.

## Key Design Features

**Direct Property Access**: `ModelSystem` provides immediate access to geometric properties like `lattice_vectors`, `positions`, and `periodic_boundary_conditions` without requiring navigation through nested subsections. This reflects the fact that a model system fundamentally is a geometric entity.

**Hierarchical Navigation**: Systems can be nested through the `sub_systems` subsection, enabling the description of complex structures like interfaces, heterostructures, or active sites within bulk materials. This navigation happens vertically through the system hierarchy, with each subsystem being itself a complete `ModelSystem`.

**Alternative Representations**: Each `ModelSystem`, at any level of the hierarchy, can have alternative geometric views (primitive cells, conventional cells, supercells) stored in the `representations` subsection. This provides lateral navigation to different geometric perspectives of the same physical system without changing your position in the hierarchy.

**Automatic Normalization**: When `is_representative=True`, the normalization process automatically generates symmetry information, chemical formulas, primitive/conventional cell representations, and system classification (bulk, surface, molecule, etc.).

## Key Components

### Geometric and Structural Properties (via Representation)

The `ModelSystem` inherits all geometric properties from the `Representation` base class, providing direct access to:

- **Cell geometry**: `lattice_vectors`, `periodic_boundary_conditions`
- **Atomic positions**: `positions` (Cartesian coordinates), `fractional_coordinates` (relative to lattice vectors)
- **Symmetry information**: `wyckoff_letters`, `equivalent_atoms`
- **Geometric measures**: `volume`, `area`, `length`

All geometric data follows a simple convention: values are expressed in an implicit Cartesian coordinate system (x, y, z). The frame itself is not stored—it's just the convention used to interpret the numbers.

See [Representation Architecture](representation.md) for detailed documentation of coordinate systems, these properties, and the design philosophy behind the unified architecture.

### Particle States

The `particle_states` subsection contains `ParticleState` instances (typically `AtomsState` for atomic systems) that describe each particle or group of particles in the system:

```python
from nomad_simulations.schema_packages.atoms_state import AtomsState

model_system = ModelSystem()
for symbol in ['Si', 'Si']:
    atom = AtomsState(chemical_symbol=symbol)
    model_system.particle_states.append(atom)
```

Each `AtomsState` can include electronic structure information through the `electronic_state` field. See [Electronic States](../atoms_state/electronic_states.md) for details on describing electronic configurations.

### Alternative Representations

The `representations` subsection stores `AlternativeRepresentation` instances that provide different geometric views of the same physical system:

```python
from nomad_simulations.schema_packages.model_system import AlternativeRepresentation

primitive = AlternativeRepresentation(
    name='primitive',
    crystal_cell_type='primitive',
    lattice_vectors=primitive_lattice_vectors
)
model_system.representations.append(primitive)
```

Common use cases include:

- Primitive cells with minimal volume
- Conventional cells following crystallographic standards
- Supercells for defect calculations or large-scale simulations

### Symmetry Information

The `symmetry` subsection contains a `Symmetry` instance that describes the space group, point group, and Bravais lattice of the system. This information is typically populated automatically during normalization through integration with the MatID symmetry analyzer:

```python
# After normalization with is_representative=True
if model_system.symmetry:
    space_group = model_system.symmetry.space_group_number
    point_group = model_system.symmetry.point_group_symbol
```

The `Symmetry` class includes a reference to the specific representation it describes through the `atomic_cell_ref` quantity.

### Chemical Formulas

The `chemical_formula` subsection contains a `ChemicalFormula` instance providing various representations of the system's composition:

- Reduced formula (e.g., "SiO2")
- Hill notation
- Anonymous formula (e.g., "A2B")
- Descriptive formula

These are generated automatically during normalization based on the particle states.

### Hierarchical Sub-systems

The `sub_systems` subsection enables description of hierarchical compositions where a system contains other systems as components. This provides vertical navigation through the physical decomposition of the system:

```python
# Create bulk system with an active site
bulk = ModelSystem(
    is_representative=True,
    lattice_vectors=...,
    # ... bulk properties
)

# Define active site as sub-system
active_site = ModelSystem(
    type='active_atom',
    particle_indices=[0, 5, 12]  # References particles in parent
)
bulk.sub_systems.append(active_site)

# Navigate down the hierarchy
for subsystem in bulk.sub_systems:
    # Each subsystem is itself a ModelSystem with direct access to geometry
    positions = subsystem.positions
    lattice = subsystem.lattice_vectors

    # And each can have its own alternative representations
    for rep in subsystem.representations:
        if rep.name == 'primitive':
            primitive_lattice = rep.lattice_vectors
```

Sub-systems are defined through the `branch_label`, `branch_depth`, `particle_indices`, and `bond_list` quantities that create a parent-child tree structure. Each subsystem at any level can have its own `representations` subsection for alternative geometric views of that specific subsystem.

## Normalization Process

The `ModelSystem.normalize()` method performs several important tasks when `is_representative=True`:

1. **Parent System normalization**: Executes base class normalization logic
2. **Particle state reassignment**: Validates and organizes particle states
3. **System type and dimensionality**: Resolves whether the system is bulk, surface, molecule, etc., and determines dimensionality (0D, 1D, 2D, 3D)
4. **Symmetry analysis**: For bulk systems, analyzes crystal symmetry and generates primitive and conventional cell representations
5. **Chemical formula generation**: Creates chemical formula descriptions from particle states

The normalization order ensures that dependencies between different components are respected. For example, symmetry analysis requires valid particle positions, and chemical formula generation requires properly initialized particle states.

See [Normalization](../normalize.md) for more details on the normalization system across NOMAD simulations schema.

## Quick Start Examples

### Simple Crystal

```python
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.atoms_state import AtomsState
import numpy as np
from nomad.units import ureg

# Create silicon crystal
silicon = ModelSystem(is_representative=True)

# Set cell geometry
silicon.lattice_vectors = np.array([
    [5.43, 0.0, 0.0],
    [0.0, 5.43, 0.0],
    [0.0, 0.0, 5.43]
]) * ureg.angstrom
silicon.periodic_boundary_conditions = [True, True, True]

# Add atoms
positions = np.array([
    [0.0, 0.0, 0.0],
    [1.3575, 1.3575, 1.3575]
]) * ureg.angstrom
silicon.positions = positions

for i in range(2):
    atom = AtomsState(chemical_symbol='Si')
    silicon.particle_states.append(atom)

# Normalization will generate symmetry info and chemical formulas
# (archive and logger are provided by the NOMAD normalization context)
silicon.normalize(archive, logger)

# Access results
print(f"Space group: {silicon.symmetry.space_group_number}")
print(f"Formula: {silicon.chemical_formula.reduced}")
```

### Working with Alternative Representations

```python
# After normalization, access alternative representations
for rep in silicon.representations:
    if rep.name == 'primitive':
        print(f"Primitive cell volume: {rep.volume}")
    elif rep.name == 'conventional':
        print(f"Conventional cell lattice: {rep.lattice_vectors}")

# Convert specific representation to ASE Atoms object
primitive_atoms = silicon.to_ase_atoms(representation_index=0)
conventional_atoms = silicon.to_ase_atoms(representation_index=1)
```

### Heterostructure with Sub-systems

```python
# Create interface system
interface = ModelSystem(is_representative=True)
interface.lattice_vectors = ...
interface.positions = ...

# Add particle states for both materials
for symbol in material_A_symbols + material_B_symbols:
    atom = AtomsState(chemical_symbol=symbol)
    interface.particle_states.append(atom)

# Define material A region as sub-system
material_A = ModelSystem(
    type='region',
    branch_label='Material A',
    particle_indices=list(range(len(material_A_symbols)))
)
interface.sub_systems.append(material_A)

# Define material B region as sub-system
material_B = ModelSystem(
    type='region',
    branch_label='Material B',
    particle_indices=list(range(len(material_A_symbols),
                                len(material_A_symbols) + len(material_B_symbols)))
)
interface.sub_systems.append(material_B)
```

## Important Flags and Settings

**`is_representative` (boolean)**: Controls whether this `ModelSystem` should undergo full normalization including symmetry analysis and formula generation. Typically set to `True` for the primary system description and `False` for sub-systems or intermediate calculations.

**`type` (string)**: Describes the role of this system in the context of hierarchical compositions. Common values include:

- `'bulk'`: Three-dimensionally periodic crystal
- `'surface'`: Two-dimensionally periodic surface or slab
- `'molecule / cluster'`: Zero-dimensional molecular or cluster system
- `'active_atom'`: Specific atoms involved in a chemical reaction or property
- `'region'`: A spatial region within a larger system

**`branch_label` (string)**: Human-readable label for this system when it appears as a sub-system in a hierarchical tree.

**`branch_depth` (integer)**: Depth of this system in the hierarchical tree (0 for root, 1 for direct children, etc.).

## See Also

- [Representation Architecture](representation.md): Detailed documentation of the geometric representation design
- [Electronic States](../atoms_state/electronic_states.md): How to describe electronic configurations of atoms
- [Normalization](../normalize.md): Overview of the normalization system
- [General Schema Overview](../general.md): Introduction to the NOMAD simulations schema package
