# Thermodynamics

**Purpose.** Thermodynamic state functions and models.
**In scope:** state functions, derived thermodynamic curves
**Out of scope:** MD raw trajectories (see Results)

## Relationship map

!!! tip "Interactive Diagram"
    **Click on the diagram below to zoom in.** Click again to zoom out.
    
    The diagram shows the relationships between the key sections in this vertical domain.


![thermo_0 diagram](../assets/diagrams/thermo_0.svg){: style="width: 80%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `Thermodynamics` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.thermodynamics.Thermodynamics){:target="_blank"} |
| `ThermodynamicsModel` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.thermodynamics.ThermodynamicsModel){:target="_blank"} |
| `ThermodynamicsResults` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.thermodynamics.ThermodynamicsResults){:target="_blank"} |
| `HeatCapacity` | Amount of heat to be supplied to a material to produce a unit change in its temperature. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.HeatCapacity){:target="_blank"} |
| `Entropy` | A measure of the disorder or randomness in a system. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.Entropy){:target="_blank"} |
| `HelmholtzFreeEnergy` | The energy available to do work in a system at constant volume and temperature, given by `InternalEnergy` - `Temperature` * `Entropy`. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.HelmholtzFreeEnergy){:target="_blank"} |
| `GibbsFreeEnergy` | The energy available to do work in a system at constant temperature and pressure, given by `Enthalpy` - `Temperature` * `Entropy`. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.GibbsFreeEnergy){:target="_blank"} |
| `Enthalpy` | The total heat content of a system, defined as 'InternalEnergy' + 'Pressure' * 'Volume'. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.Enthalpy){:target="_blank"} |
| `InternalEnergy` | The total energy contained within a system, encompassing both kinetic and potential energies of the particles. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.InternalEnergy){:target="_blank"} |


## Micro-examples

=== "YAML"

    ```yaml
    Thermodynamics: {}
    ThermodynamicsModel: {}
    ThermodynamicsResults:
      n_values:
      - null
      temperature:
      - null
      pressure:
      - null
    HeatCapacity:
      value:
      - null
    Entropy:
      value:
      - null
    HelmholtzFreeEnergy: {}
    GibbsFreeEnergy: {}
    Enthalpy: {}
    InternalEnergy: {}
    ```