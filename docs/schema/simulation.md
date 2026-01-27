# Simulation Entry

**Purpose:** Root entry point for simulations: Simulation, BaseSimulation, and Program

**In scope:**

Root Simulation section that contains all simulation metadata

Timing information (cpu1_start, cpu1_end, wall_start, wall_end)

Program details (name, version, link)

Entry point that references the four main subsections

**Out of scope:**

ModelSystem details (see model_system vertical)

ModelMethod details (see model_method vertical)

Outputs details (see dedicated output verticals)

Workflow classes (separate schema)

## Relationship map

!!! tip "Interactive Diagram"
    **Click on the diagram below to zoom in.** Click again to zoom out.

    The diagram shows the relationships between the key sections in this vertical domain.


![simulation_0 diagram](../assets/diagrams/simulation_0.svg){: style="width: 80%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `Simulation` | A `Simulation` is a computational calculation that produces output data from a given input model system and input (model) methodological parameters. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.general.Simulation){:target="_blank"} |
| `BaseSimulation` | A computational simulation that produces output data from a given input model system and input methodological parameters. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.general.BaseSimulation){:target="_blank"} |
| `Program` | A base section used to specify a well-defined program used for computation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.general.Program){:target="_blank"} |


## Micro-examples

=== "YAML"

    ```yaml
    Simulation:
      representative_system_index:
      - null
      model_system:
      - {}
      model_method:
      - {}
      outputs:
      - {}
    BaseSimulation:
      datetime_end:
      - null
      cpu1_start:
      - null
      cpu1_end:
      - null
      wall_start:
      - null
      wall_end:
      - null
      program: {}
    Program:
      name:
      - null
      version:
      - null
      link:
      - null
      version_internal:
      - null
      subroutine_name_internal:
      - null
      compilation_host:
      - null
    ```