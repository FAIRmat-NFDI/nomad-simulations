# Outputs Base

**Purpose:** Base output structure and common property definitions

**In scope:**

- Outputs section that references ModelSystem and ModelMethod
- SCFOutputs with scf_steps for iteration history
- PhysicalProperty base class for all computed properties
- Property contributions and derivations
- SCF convergence checking

**Out of scope:**

- Specific property types
- Electronic structure properties
- Many-body properties
- Spectroscopic properties
- Thermodynamic properties

## Relationship map


![outputs_0 diagram](../assets/diagrams/outputs_0.svg){: style="width: 80%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}

<div style="font-size: 0.9em; color: #666; margin-top: 8px; margin-bottom: 8px;">
<b>Legend:</b>
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="20" y1="6" x2="4" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="4,6 8,3 8,9" fill="none" stroke="currentColor" stroke-width="1.5"/></svg> inheritance ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> containment ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2,2"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> reference
</div>


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `Outputs` | Output properties of a simulation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.outputs.Outputs){:target="_blank"} |
| `SCFOutputs` | This section contains the self-consistent (SCF) steps performed to converge an output property. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.outputs.SCFOutputs){:target="_blank"} |
| `PhysicalProperty` | A base section for computational output properties, containing all relevant (meta)data. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.physical_property.PhysicalProperty){:target="_blank"} |


## Micro-examples

=== "YAML"

    ```yaml
    Outputs:
      model_system_ref:
      - null
      model_method_ref:
      - null
      chemical_potentials:
      - {}
      crystal_field_splittings:
      - {}
      hopping_matrices:
      - {}
      electronic_eigenvalues:
      - {}
      electronic_band_gaps:
      - {}
      electronic_dos:
      - {}
      fermi_surfaces:
      - {}
      electronic_band_structures:
      - {}
      occupancies:
      - {}
      electronic_greens_functions:
      - {}
      electronic_self_energies:
      - {}
      hybridization_functions:
      - {}
      quasiparticle_weights:
      - {}
      permittivities:
      - {}
      absorption_spectra:
      - {}
      xas_spectra:
      - {}
      total_energies:
      - {}
      kinetic_energies:
      - {}
      potential_energies:
      - {}
      total_forces:
      - {}
      temperatures:
      - {}
    SCFOutputs:
      scf_steps:
      - {}
    PhysicalProperty:
      name:
      - null
      iri: ''
      type:
      - null
      contribution_type:
      - null
      label:
      - null
      entity_ref:
      - null
      is_derived: false
      physical_property_ref:
      - null
      is_scf_converged:
      - null
      self_consistency_ref:
      - null
      contributions:
      - {}
    ```