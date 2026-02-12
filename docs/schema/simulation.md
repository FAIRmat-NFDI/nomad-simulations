# Simulation Entry

**Purpose:** Root entry point for simulations: Simulation, BaseSimulation, and Program

**In scope:**

- Root Simulation section that contains all simulation metadata
- Timing information (cpu1_start, cpu1_end, wall_start, wall_end)
- Program details (name, version, link)
- Entry point that references the four main subsections

**Out of scope:**

- ModelSystem details
- ModelMethod details
- Outputs details
- Workflow classes (separate schema)

## Relationship map


```mermaid
classDiagram
    class BaseSimulation
    class ModelMethod
    class ModelSystem
    class Outputs
    class Program
    class Simulation
    BaseSimulation <|-- Simulation
    BaseSimulation --> Program : program
    Simulation --> ModelMethod : model_method
    Simulation --> ModelSystem : model_system
    Simulation --> Outputs : outputs
```

**Legend**

- `Parent <|-- Child`: inheritance (`Child` extends `Parent`)
- `Owner --> SubSection`: containment/subsection relationship
- `Source ..> Target`: typed reference from one section to another


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `Simulation` | A `Simulation` is a computational calculation that produces output data from a given input model system and input (model) methodological parameters. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.general.Simulation){:target="_blank"} |
| `BaseSimulation` | A computational simulation that produces output data from a given input model system and input methodological parameters. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.general.BaseSimulation){:target="_blank"} |
| `Program` | A base section used to specify a well-defined program used for computation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.general.Program){:target="_blank"} |


## Quantities by section

### `Simulation`

| Quantity | Type | Description |
|---|---|---|
| `representative_system_index` | m_int32(int32) | The index of the "representative system" in the `model_system` list. |

### `BaseSimulation`

*This section has no direct quantities.*

### `Program`

| Quantity | Type | Description |
|---|---|---|
| `name` | m_str(str) | The name of the program. |
| `version` | m_str(str) | The version label of the program. |
| `link` | m_str(str) | Website link to the program in published information. |
| `version_internal` | m_str(str) | Specifies a program version tag used internally for development purposes. Any kind of tagging system is supported, including git commit hashes. |
| `subroutine_name_internal` | m_str(str) | <details><summary>Specifies the name of the subroutine of the program at large.</summary>Specifies the name of the subroutine of the program at large.<br>This only applies when the routine produced (almost) all of the output,<br>so the naming is representative. This naming is mostly meant for users<br>who are familiar with the program's structure.</details> |
| `compilation_host` | m_str(str) | Specifies the host on which the program was compiled. |

