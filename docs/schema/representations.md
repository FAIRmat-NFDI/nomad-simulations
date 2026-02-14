# Alternative Representations

**Purpose:** AlternativeRepresentation subsection details: transforms and mapping to a reference representation

**In scope:**

- AlternativeRepresentation subsection of ModelSystem
- Reference representation linkage
- Transformation matrix and origin shift between representations
- How alternative cells are mapped from the original representation

## Relationship map


```mermaid
classDiagram
    class AlternativeRepresentation
```


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `AlternativeRepresentation` | A representation relative to another, reference representation, typically the original computed system. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.AlternativeRepresentation){:target="_blank"} |


## Quantities by section

### `AlternativeRepresentation`

| Quantity | Type | Description |
|---|---|---|
| `origin_shift` | m_float64(float64) (shape: [3]) | <details><summary>Translation vector relating the origin of this representation to the reference r...</summary>Translation vector relating the origin of this representation to the reference representation,<br>expressed in fractional coordinates. Together with transformation_matrix, defines how fractional<br>coordinates transform between representations: x_alt = P @ x_ref + p, where both representations<br>use the same implicit Cartesian frame but different lattice vectors. Commonly used to relate<br>input cells to standardized conventional cells in symmetry analysis (e.g., from [spglib](https://spglib.readthedocs.io/en/latest/definition.html)).</details> |
| `transformation_matrix` | m_float64(float64) (shape: [3, 3]) | <details><summary>Transformation matrix P relating lattice vectors between this representation and...</summary>Transformation matrix P relating lattice vectors between this representation and the reference<br>representation. Lattice vectors transform as: (a_alt, b_alt, c_alt) = (a_ref, b_ref, c_ref) @ P^-1.<br>Together with origin_shift, defines how fractional coordinates transform: x_alt = P @ x_ref + p.<br>Both representations use the same implicit Cartesian frame; this matrix only changes how fractional<br>coordinates are expressed relative to different lattice vectors. Commonly used in symmetry analysis<br>to relate input cells to standardized conventional cells (e.g., from [spglib](https://spglib.readthedocs.io/en/latest/definition.html)).</details> |
| `crystal_cell_type` | Enum | Representation type of the cell structure. It might be: - 'primitive' as the primitive unit cell, - 'conventional' as the conventional cell used for referencing. |
| `supercell_matrix` | m_int32(int32) (shape: [3, 3]) | <details><summary>Specifies the matrix that transforms the primitive unit cell into the supercell ...</summary>Specifies the matrix that transforms the primitive unit cell into the supercell in<br>which the actual calculation is performed. In the easiest example, it is a diagonal<br>matrix whose elements multiply the lattice_vectors, e.g., [[3, 0, 0], [0, 3, 0], [0, 0, 3]]<br>is a $3 x 3 x 3$ superlattice.</details> |

