# Representation Architecture

## Introduction

The `Representation` class handles the geometric details of a particulate system in NOMAD simulations. It consolidates geometric properties (volume, area, length), cell properties (lattice vectors, periodic boundary conditions), and structural properties (atomic positions, fractional coordinates, symmetry information) into a single coherent interface.

`ModelSystem` combines `Representation` with the system hierarchy navigation capabilities, giving each system in the hierarchy direct access to its geometric data. This means properties like `lattice_vectors` and `positions` are available directly on `ModelSystem` without needing separate cell objects.

## Coordinate Systems and Geometric Data

The `Representation` class provides direct access to geometric cell information. `ModelSystem` (which inherits from `Representation`) adds the atomic positions. All geometric data follows a simple convention: values are expressed in an implicit Cartesian coordinate system with axes ordered as (x, y, z). This frame is not stored explicitly—it's simply the convention used to interpret the numerical values.

### Understanding the Coordinate Convention

The geometric quantities use a consistent implicit Cartesian frame:

- **`lattice_vectors`** (in `Representation`): A 3×3 matrix where each row is a lattice vector in the implicit Cartesian frame. The first row is vector a, the second is vector b, and the third is vector c.

- **`fractional_coordinates`** (in `Representation`): Dimensionless coordinates relative to the lattice vectors, typically in the range [0, 1] within the unit cell.

- **`positions`** (in `ModelSystem`): Cartesian coordinates (x, y, z) of each atom in the top-level system. The orientation of the frame comes from the simulation code or parser that generated the data. Subsystems reference these positions via `particle_indices`.

### Setting Geometric Properties

```python
--8<-- "snippets/explanation/model_system/representation/block_01.py"
```

This direct access means the geometric description is inherently part of what a model system is, rather than being stored in a separate subsection.

## Alternative Representations

The `AlternativeRepresentation` class extends `Representation` with additional properties needed for derived or transformed views of the system. These include transformation matrices and origin shifts that relate different cell choices (primitive vs. conventional, standardized vs. input), as well as cell type indicators.

Importantly, all alternative representations use the **same implicit Cartesian frame** as the original system. The `transformation_matrix` and `origin_shift` describe how fractional coordinates and lattice vectors relate between representations, not transformations of the Cartesian basis itself. This follows the approach used in symmetry analysis tools like spglib, where different cell choices (primitive, conventional, standardized) are expressed in a common Cartesian reference frame.

Alternative representations are stored in the `representations` subsection of `ModelSystem`:

```python
--8<-- "snippets/explanation/model_system/representation/block_02.py"
```

This pattern allows the same physical system to be described from multiple geometric perspectives while maintaining the original parser output as the primary data on the `ModelSystem` itself.

## Integration with Symmetry Analysis

The `Representation` architecture integrates naturally with symmetry analysis. When `ModelSystem.normalize()` is called with `is_representative=True`, the symmetry analysis workflow automatically generates primitive and conventional cell representations:

```python
--8<-- "snippets/explanation/model_system/representation/block_03.py"
```

## Usage Patterns and Best Practices

### When to Use Alternative Representations

Alternative representations should be used when you need to describe the same physical system from different geometric perspectives: primitive cells (minimal unit cell with smallest volume), conventional cells (standard unit cells aligned with crystallographic conventions), supercells (larger cells created by replicating the unit cell), or transformed cells (rotated or transformed for specific computational purposes). Each representation in the `representations` subsection should have a descriptive `name` that clearly indicates its purpose.

### Direct vs. Subsection Storage

The design principle is straightforward: the original system description (as provided by the parser or user) lives directly on `ModelSystem` properties, while derived or alternative views are stored in the `representations` subsection. This maintains a clear provenance for the data.

### Working with ASE Atoms Objects

The `to_ase_atoms()` method allows you to convert any geometric representation to ASE format. By default, it uses the cell geometry (lattice vectors and periodic boundary conditions) directly from `ModelSystem`. The optional `representation_index` parameter lets you select an alternative representation's cell geometry instead, while atomic positions always come from the main `ModelSystem`:

```python
--8<-- "snippets/explanation/model_system/representation/block_04.py"
```

This is particularly useful when you need to perform ASE-based analyses with different cell definitions. For example, you might want to compute phonons in the primitive cell or visualize the structure in the conventional cell, all while using the same atomic positions from the original system.

The separation between atomic positions (from `ModelSystem`) and cell geometry (from `ModelSystem` or `ModelSystem.representations[index]`) reflects the fact that alternative representations typically provide different unit cell choices for the same atomic structure.

### Programmatic Access to Named Representations

When searching for a specific representation by name, use a simple loop:

```python
--8<-- "snippets/explanation/model_system/representation/block_05.py"
```

This pattern is used throughout the NOMAD simulations schema, particularly in numerical settings where primitive cells are often required for k-space sampling.

## Representation Does Not Interfere with Navigation

The `Representation` class focuses solely on geometric details and does not affect how you navigate through system hierarchies. Navigation through the subsystem hierarchy (via `ModelSystem.sub_systems`) is handled separately and is documented in the [ModelSystem Overview](overview.md).

What `Representation` does provide is the ability to access alternative geometric views at any point in the hierarchy. Each `ModelSystem`, at any level, can have its own `representations` subsection containing different geometric perspectives of that specific system:

```python
--8<-- "snippets/explanation/model_system/representation/block_06.py"
```

This means you can explore different geometric descriptions (primitive cells, conventional cells, supercells) without changing your position in the system hierarchy.

## See Also

- [ModelSystem Overview](overview.md): General introduction to the ModelSystem class
- [Electronic States](electronic_states.md): Similar hierarchical design pattern for electronic structure
- [Normalization](../../schema_development/normalize.md): How normalization populates alternative representations
