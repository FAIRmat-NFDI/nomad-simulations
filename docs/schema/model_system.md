# Model System

**Purpose:** Complete ModelSystem tree: geometric spaces, cells, symmetry, and particle organization

**In scope:**

- ModelSystem as the root of the system tree
- Geometric spaces: Cell and AtomicCell with lattice vectors
- Symmetry information: space groups, point groups, Bravais lattices
- Chemical formulas: descriptive, reduced, IUPAC, Hill, anonymous
- Particle states: AtomsState for atoms, CGBeadState for coarse-grained beads
- Recursive sub_systems containment (ModelSystem contains ModelSystem)
- Positions, velocities, particle_indices
- System type and dimensionality

**Out of scope:**

- Detailed atomic properties like orbitals
- Core holes and Hubbard interactions
- Methods that use the system
- Outputs computed from the system

## Relationship map


![model_system_0 diagram](../assets/diagrams/model_system_0.svg){: style="width: 80%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}

<div style="font-size: 0.9em; color: #666; margin-top: 8px; margin-bottom: 8px;">
<b>Legend:</b>
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="20" y1="6" x2="4" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="4,6 8,3 8,9" fill="none" stroke="currentColor" stroke-width="1.5"/></svg> inheritance ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> containment ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2,2"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> reference
</div>


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `ModelSystem` | Model system used as an input for simulating the material. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.ModelSystem){:target="_blank"} |
| `GeometricSpace` | A base section used to define geometrical spaces and their entities. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.GeometricSpace){:target="_blank"} |
| `Cell` | A base section used to specify the cell quantities of a system at a given moment in time. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.Cell){:target="_blank"} |
| `AtomicCell` | A base section used to specify the atomic cell information of a system. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.AtomicCell){:target="_blank"} |
| `Symmetry` | A base section used to specify the symmetry of the `AtomicCell`. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.Symmetry){:target="_blank"} |
| `ChemicalFormula` | A base section used to store the chemical formulas of a `ModelSystem` in different formats. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.ChemicalFormula){:target="_blank"} |
| `ParticleState` | Generic base section representing the state of a particle in a simulation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.atoms_state.ParticleState){:target="_blank"} |
| `AtomsState` | A base section to define each atom state information. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.atoms_state.AtomsState){:target="_blank"} |
| `CGBeadState` | A section to define coarse-grained bead state information. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.atoms_state.CGBeadState){:target="_blank"} |


## Micro-examples

=== "YAML"

    ```yaml
    ModelSystem:
      name:
      - null
      type:
      - null
      dimensionality:
      - null
      is_representative: false
      time_step:
      - null
      branch_label:
      - null
      branch_depth:
      - null
      particle_indices:
      - null
      n_particles:
      - null
      positions:
      - null
      velocities:
      - null
      bond_list:
      - null
      composition_formula:
      - null
      total_charge:
      - null
      total_spin:
      - null
      cell:
      - {}
      symmetry:
      - {}
      chemical_formula: {}
      particle_states:
      - {}
      sub_systems:
      - {}
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
    Symmetry:
      bravais_lattice:
      - null
      hall_symbol:
      - null
      point_group_symbol:
      - null
      space_group_number:
      - null
      space_group_symbol:
      - null
      strukturbericht_designation:
      - null
      prototype_formula:
      - null
      prototype_aflow_id:
      - null
      atomic_cell_ref:
      - null
    ChemicalFormula:
      descriptive:
      - null
      reduced:
      - null
      iupac:
      - null
      hill:
      - null
      anonymous:
      - null
    ParticleState:
      label:
      - null
    AtomsState:
      chemical_symbol:
      - null
      atomic_number:
      - null
      charge: 0
      spin: 0
      label:
      - null
      orbitals_state:
      - {}
      core_hole: {}
      hubbard_interactions: {}
    CGBeadState:
      bead_symbol:
      - null
      label:
      - null
      alt_labels:
      - null
      mass:
      - null
      charge:
      - null
    ```