# `ModelSystem`

## Pages in This Section

- [Representation Architecture](representation.md)
- [Electronic States](electronic_states.md)
- [Model System Usage Guidelines](../../schema_development/model_system_usage_guidelines.md)

## Schema Navigation References

- [Model System](../../schema/model_system.md)
- [Alternative Representations](../../schema/representations.md)
- [Chemical Formula](../../schema/chemical_formula.md)
- [Particle States](../../schema/particle_states.md)
- [Symmetry](../../schema/symmetry.md)

## Overview

The `ModelSystem` class represents the physical system that serves as input for simulation calculations in NOMAD. It provides a comprehensive description of the atomic or coarse-grained structure, including particle positions, cell geometry, symmetry information, and chemical composition.

For complete field-level structure, see the schema navigation references above.

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
--8<-- "snippets/explanation/model_system/model_system/block_01.py"
```

Each `AtomsState` can include electronic structure information through the `electronic_state` field. See [Electronic States](electronic_states.md) for details on describing electronic configurations.

### Alternative Representations

The `representations` subsection stores `AlternativeRepresentation` instances that provide different geometric views of the same physical system:

```python
--8<-- "snippets/explanation/model_system/model_system/block_02.py"
```

Common use cases include:

- Primitive cells with minimal volume
- Conventional cells following crystallographic standards
- Supercells for defect calculations or large-scale simulations

### Symmetry Information

The `symmetry` subsection contains a `Symmetry` instance that describes the space group, point group, and Bravais lattice of the system. This information is typically populated automatically during normalization through integration with the MatID symmetry analyzer:

```python
--8<-- "snippets/explanation/model_system/model_system/block_03.py"
```

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
--8<-- "snippets/explanation/model_system/model_system/block_04.py"
```

Sub-systems are defined through the `branch_label`, `branch_depth`, `particle_indices`, and `bond_list` quantities that create a parent-child tree structure. Each subsystem at any level can have its own `representations` subsection for alternative geometric views of that specific subsystem.

### Hierarchy and Composition Behavior

When a ModelSystem subsystem hierarchy is populated, normalization resolves
branch depth and composition labels consistently along the tree. In practice:

- root systems summarize child groups in `composition_formula`,
- intermediate groups summarize repeated motifs,
- leaf systems resolve to atom-level formulas.

Keep subsystem-hierarchy semantics (`sub_systems`) distinct from alternative geometric
views (`representations`).

## Derived Behavior During Normalization

When `is_representative=True`, normalization enriches a `ModelSystem` with derived information that is expected from a complete structural description.

This includes:

1. **Validated particle-state organization**: particle-state information is checked and arranged consistently.
2. **System type and dimensionality**: the system is classified as bulk, surface, molecule, and so on, together with its effective dimensionality.
3. **Symmetry information and standard cells**: bulk systems can gain symmetry metadata together with primitive and conventional cell representations.
4. **Chemical formulas**: composition summaries are derived from the populated particle states.

These derived results depend on the structural data already present in the archive. For example, symmetry analysis depends on valid geometry, and chemical formulas depend on the populated particle states.

See [Normalization](../../schema_development/normalize.md) for more details on the normalization system across NOMAD simulations schema.

## Quick Start Examples

### Simple Crystal

```python
--8<-- "snippets/explanation/model_system/model_system/block_05.py"
```

### Working with Alternative Representations

```python
--8<-- "snippets/explanation/model_system/model_system/block_06.py"
```

### Heterostructure with Sub-systems

```python
--8<-- "snippets/explanation/model_system/model_system/block_07.py"
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

## Related Pages

- [Representation Architecture](representation.md): Detailed documentation of the geometric representation design
- [Electronic States](electronic_states.md): How to describe electronic configurations of atoms
- [Normalization](../../schema_development/normalize.md): Overview of the normalization system
- [General Schema Overview](../overview.md): Introduction to the NOMAD simulations schema package
