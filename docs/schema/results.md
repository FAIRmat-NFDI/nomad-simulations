# Results & Provenance

**Purpose.** Canonical scientific outputs and provenance bundles.
**In scope:** band structures, DOS, gaps, SCF history, trajectories
**Out of scope:** raw logs, plot styling

## Relationship map

!!! tip "Interactive Diagram"
    **Click on the diagram below to zoom in.** Click again to zoom out.
    
    The diagram shows the relationships between the key sections in this vertical domain.


![results_0 diagram](../assets/diagrams/results_0.png){: style="width: 80%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `Outputs` | Output properties of a simulation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.outputs.Outputs){:target="_blank"} |
| `ElectronicStructureResults` | Contains definitions for results of an electronic structure simulation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.general.ElectronicStructureResults){:target="_blank"} |
| `ElectronicBandStructure` | Accessible energies by the charges (electrons and holes) in the reciprocal space. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.band_structure.ElectronicBandStructure){:target="_blank"} |
| `ElectronicDensityOfStates` | Number of electronic states accessible for the charges per energy and per volume. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.spectral_profile.ElectronicDensityOfStates){:target="_blank"} |
| `ElectronicBandGap` | Energy difference between the highest occupied electronic state and the lowest unoccupied electronic state. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.band_gap.ElectronicBandGap){:target="_blank"} |
| `FermiSurface` | Energy boundary in reciprocal space that separates the filled and empty electronic states in a metal. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.fermi_surface.FermiSurface){:target="_blank"} |
| `SCFOutputs` | This section contains the self-consistent (SCF) steps performed to converge an output property. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.outputs.SCFOutputs){:target="_blank"} |
| `TrajectoryOutputs` | This section contains output properties that depend on a single system, but were calculated as part of a trajectory (e.g., temperatures from a molecul... | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.outputs.TrajectoryOutputs){:target="_blank"} |
| `ThermodynamicsResults` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.thermodynamics.ThermodynamicsResults){:target="_blank"} |
| `GeometryOptimizationResults` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.geometry_optimization.GeometryOptimizationResults){:target="_blank"} |


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
    ElectronicStructureResults:
      dos:
      - null
    ElectronicBandStructure:
      k_path: {}
    ElectronicDensityOfStates:
      spin_channel:
      - null
      energies_origin:
      - null
      normalization_factor:
      - null
      energies: {}
      projected_dos:
      - {}
    ElectronicBandGap:
      type:
      - null
      momentum_transfer:
      - null
      spin_channel:
      - null
      value:
      - null
    FermiSurface:
      n_bands:
      - null
    SCFOutputs:
      scf_steps:
      - {}
    TrajectoryOutputs:
      time:
      - null
    ThermodynamicsResults:
      n_values:
      - null
      temperature:
      - null
      pressure:
      - null
    GeometryOptimizationResults:
      n_steps:
      - null
      energies:
      - null
      steps:
      - null
      final_energy_difference:
      - null
      final_force_maximum:
      - null
      final_displacement_maximum:
      - null
      is_converged_geometry:
      - null
    ```