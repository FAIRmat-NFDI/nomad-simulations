# Model System

**Purpose:** Root ModelSystem section containing the complete system tree

**In scope:**

- ModelSystem as the root of the system tree
- Recursive sub_systems containment (ModelSystem contains ModelSystem)
- System type and dimensionality
- References to Cell, ParticleState, Symmetry, ChemicalFormula subsections

**Out of scope:**

- Cell and geometric details
- Particle state details
- Symmetry details
- Chemical formula details
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
    ```