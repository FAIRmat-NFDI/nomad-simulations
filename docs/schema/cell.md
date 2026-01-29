# Cell and Geometric Spaces

**Purpose:** Geometric space hierarchy: GeometricSpace, Cell, and AtomicCell with lattice vectors

**In scope:**

- GeometricSpace: base section for defining geometrical spaces
- Cell: cell quantities and lattice vectors
- AtomicCell: atomic cell information extending Cell
- Lattice vectors, periodic boundary conditions
- Positions and cell geometry

**Out of scope:**

- Particle states within the cell
- Symmetry information
- Chemical formulas

## Relationship map


![cell_0 diagram](../assets/diagrams/cell_0.svg){: style="width: 80%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}

<div style="font-size: 0.9em; color: #666; margin-top: 8px; margin-bottom: 8px;">
<b>Legend:</b>
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="20" y1="6" x2="4" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="4,6 8,3 8,9" fill="none" stroke="currentColor" stroke-width="1.5"/></svg> inheritance ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> containment ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2,2"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> reference
</div>


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `GeometricSpace` | A base section used to define geometrical spaces and their entities. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.GeometricSpace){:target="_blank"} |
| `Cell` | A base section used to specify the cell quantities of a system at a given moment in time. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.Cell){:target="_blank"} |
| `AtomicCell` | A base section used to specify the atomic cell information of a system. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.AtomicCell){:target="_blank"} |


## Micro-examples

=== "YAML"

    ```yaml
    GeometricSpace:
      length_vector_a:
      - null
      length_vector_b:
      - null
      length_vector_c:
      - null
      angle_vectors_b_c:
      - null
      angle_vectors_a_c:
      - null
      angle_vectors_a_b:
      - null
      volume:
      - null
      surface_area:
      - null
      area:
      - null
      length:
      - null
      coordinates_system: cartesian
      origin_shift:
      - null
      transformation_matrix:
      - null
    Cell:
      name:
      - null
      type:
      - null
      n_cell_points:
      - null
      lattice_vectors:
      - null
      periodic_boundary_conditions:
      - null
      supercell_matrix:
      - null
    AtomicCell:
      equivalent_atoms:
      - null
      wyckoff_letters:
      - null
    ```