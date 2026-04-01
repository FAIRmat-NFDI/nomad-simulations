# Thermodynamics Workflow

**Purpose:** Thermodynamics workflow for free-energy and thermodynamic property calculations


## Relationship map


<div class="uml-diagram-card" markdown="1">

```mermaid
classDiagram
    class SerialWorkflow
    class SerialWorkflowResults
    class SimulationWorkflowMethod
    class Thermodynamics
    class ThermodynamicsMethod
    class ThermodynamicsResults
    SerialWorkflow <|-- Thermodynamics
    SimulationWorkflowMethod <|-- ThermodynamicsMethod
    SerialWorkflowResults <|-- ThermodynamicsResults
    Thermodynamics *-- ThermodynamicsMethod : method
    Thermodynamics *-- ThermodynamicsResults : results
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="54" y1="8" x2="22" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M10 8 L22 2 L22 14 Z"/></svg><span>inheritance (is-a)</span></div>
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><path class="uml-legend__head uml-legend__head--filled" d="M10 8 L16 2 L22 8 L16 14 Z"/><line class="uml-legend__line" x1="22" y1="8" x2="52" y2="8"/></svg><span>composition (has-a)</span></div>
</div>

</div>


## Quantities by Key Sections

### `SerialWorkflow`

| Section | Description | MetaInfo |
|---|---|---|
| `SerialWorkflow` | Base class for workflows where tasks are executed sequentially. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.general.SerialWorkflow){:target="_blank"} |

*This section has no direct quantities.*

### `SerialWorkflowResults`

| Section | Description | MetaInfo |
|---|---|---|
| `SerialWorkflowResults` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.general.SerialWorkflowResults){:target="_blank"} |

*This section has no direct quantities.*

### `SimulationWorkflowMethod`

| Section | Description | MetaInfo |
|---|---|---|
| `SimulationWorkflowMethod` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.general.SimulationWorkflowMethod){:target="_blank"} |

*This section has no direct quantities.*

### `Thermodynamics`

| Section | Description | MetaInfo |
|---|---|---|
| `Thermodynamics` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.thermodynamics.Thermodynamics){:target="_blank"} |

*This section has no direct quantities.*

### `ThermodynamicsMethod`

| Section | Description | MetaInfo |
|---|---|---|
| `ThermodynamicsMethod` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.thermodynamics.ThermodynamicsMethod){:target="_blank"} |

*This section has no direct quantities.*

### `ThermodynamicsResults`

| Section | Description | MetaInfo |
|---|---|---|
| `ThermodynamicsResults` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.thermodynamics.ThermodynamicsResults){:target="_blank"} |

*This section has no direct quantities.*


## Related Pages

- [Workflow Overview](../explanation/workflow/overview.md)
