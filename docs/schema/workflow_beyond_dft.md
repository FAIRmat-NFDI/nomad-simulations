# Beyond-DFT Workflow Family

**Purpose:** Beyond-DFT workflow base classes and derived GW/TB/DMFT/XS specializations

**In scope:**

- BeyondDFT inheritance backbone for workflow/method/results
- Derived families: GW, DFT+TB, DFT+TB+DMFT, DMFT+MaxEnt, and XS
- ElectronicStructureResults subsections used by beyond-DFT result classes


## Relationship map


<div class="uml-diagram-card" markdown="1">

```mermaid
classDiagram
    class BeyondDFTMethod
    class BeyondDFTResults
    class BeyondDFTWorkflow
    class DFTGWMethod
    class DFTGWResults
    class DFTGWWorkflow
    class DFTTBDMFTMethod
    class DFTTBDMFTResults
    class DFTTBDMFTWorkflow
    class DFTTBMethod
    class DFTTBResults
    class DFTTBWorkflow
    class DMFTMaxEntWorkflow
    class DMTMaxEntMethod
    class DMTMaxEntResults
    class ElectronicStructureResults
    class SerialWorkflow
    class SimulationWorkflowMethod
    class SimulationWorkflowResults
    class WorkflowConvergenceResults
    class XSMethod
    class XSResults
    class XSWorkflow
    SimulationWorkflowMethod <|-- BeyondDFTMethod
    SimulationWorkflowResults <|-- BeyondDFTResults
    SerialWorkflow <|-- BeyondDFTWorkflow
    BeyondDFTMethod <|-- DFTGWMethod
    BeyondDFTResults <|-- DFTGWResults
    BeyondDFTWorkflow <|-- DFTGWWorkflow
    BeyondDFTMethod <|-- DFTTBDMFTMethod
    BeyondDFTResults <|-- DFTTBDMFTResults
    BeyondDFTWorkflow <|-- DFTTBDMFTWorkflow
    BeyondDFTMethod <|-- DFTTBMethod
    BeyondDFTResults <|-- DFTTBResults
    BeyondDFTWorkflow <|-- DFTTBWorkflow
    BeyondDFTWorkflow <|-- DMFTMaxEntWorkflow
    BeyondDFTMethod <|-- DMTMaxEntMethod
    BeyondDFTResults <|-- DMTMaxEntResults
    SimulationWorkflowResults <|-- ElectronicStructureResults
    BeyondDFTMethod <|-- XSMethod
    BeyondDFTResults <|-- XSResults
    BeyondDFTWorkflow <|-- XSWorkflow
    BeyondDFTResults *-- ElectronicStructureResults : dft
    BeyondDFTResults *-- ElectronicStructureResults : ext
    SimulationWorkflowResults *-- WorkflowConvergenceResults : convergence
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="54" y1="8" x2="22" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M10 8 L22 2 L22 14 Z"/></svg><span>inheritance (is-a)</span></div>
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><path class="uml-legend__head uml-legend__head--filled" d="M10 8 L16 2 L22 8 L16 14 Z"/><line class="uml-legend__line" x1="22" y1="8" x2="52" y2="8"/></svg><span>composition (has-a)</span></div>
</div>

</div>


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `SerialWorkflow` | Base class for workflows where tasks are executed sequentially. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.general.SerialWorkflow){:target="_blank"} |
| `SimulationWorkflowMethod` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.general.SimulationWorkflowMethod){:target="_blank"} |
| `SimulationWorkflowResults` | Base class for simulation workflow results sub-section definition. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.general.SimulationWorkflowResults){:target="_blank"} |
| `ElectronicStructureResults` | Contains definitions for results of an electronic structure simulation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.general.ElectronicStructureResults){:target="_blank"} |
| `BeyondDFTWorkflow` | Definitions for workflows based on DFT. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.beyond_dft.BeyondDFTWorkflow){:target="_blank"} |
| `BeyondDFTMethod` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.beyond_dft.BeyondDFTMethod){:target="_blank"} |
| `BeyondDFTResults` | Contains reference to DFT outputs. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.beyond_dft.BeyondDFTResults){:target="_blank"} |
| `DFTGWWorkflow` | Definitions for GW calculations based on DFT. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.gw.DFTGWWorkflow){:target="_blank"} |
| `DFTGWMethod` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.gw.DFTGWMethod){:target="_blank"} |
| `DFTGWResults` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.gw.DFTGWResults){:target="_blank"} |
| `DFTTBWorkflow` | Definitions for TB calculations based on DFT. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.tb.DFTTBWorkflow){:target="_blank"} |
| `DFTTBMethod` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.tb.DFTTBMethod){:target="_blank"} |
| `DFTTBResults` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.tb.DFTTBResults){:target="_blank"} |
| `DFTTBDMFTWorkflow` | Definitions for DMFT worklow based on DFT and TB. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.dmft.DFTTBDMFTWorkflow){:target="_blank"} |
| `DFTTBDMFTMethod` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.dmft.DFTTBDMFTMethod){:target="_blank"} |
| `DFTTBDMFTResults` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.dmft.DFTTBDMFTResults){:target="_blank"} |
| `DMFTMaxEntWorkflow` | Definitions for MaxEnt (Maximum Entropy) worklow based on DMFT. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.max_ent.DMFTMaxEntWorkflow){:target="_blank"} |
| `DMTMaxEntMethod` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.max_ent.DMTMaxEntMethod){:target="_blank"} |
| `DMTMaxEntResults` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.max_ent.DMTMaxEntResults){:target="_blank"} |
| `XSWorkflow` | Definitions for XS workflow based in DFT, GW and PhotonPolarizationWorkflow. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.xs.XSWorkflow){:target="_blank"} |
| `XSMethod` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.xs.XSMethod){:target="_blank"} |
| `XSResults` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.workflow.xs.XSResults){:target="_blank"} |


## Quantities by section

### `SerialWorkflow`

*This section has no direct quantities.*

### `SimulationWorkflowMethod`

*This section has no direct quantities.*

### `SimulationWorkflowResults`

| Quantity | Type | Description |
|---|---|---|
| `finished_normally` | m_bool(bool) | Indicates if calculation terminated normally. |
| `is_converged` | m_bool(bool) | Represents if the convergence targets have been reached (True) or not (False). |

### `ElectronicStructureResults`

| Quantity | Type | Description |
|---|---|---|
| `dos` | Reference | Reference to the electronic density of states output. |

### `BeyondDFTWorkflow`

*This section has no direct quantities.*

### `BeyondDFTMethod`

*This section has no direct quantities.*

### `BeyondDFTResults`

*This section has no direct quantities.*

### `DFTGWWorkflow`

*This section has no direct quantities.*

### `DFTGWMethod`

*This section has no direct quantities.*

### `DFTGWResults`

*This section has no direct quantities.*

### `DFTTBWorkflow`

*This section has no direct quantities.*

### `DFTTBMethod`

*This section has no direct quantities.*

### `DFTTBResults`

*This section has no direct quantities.*

### `DFTTBDMFTWorkflow`

*This section has no direct quantities.*

### `DFTTBDMFTMethod`

*This section has no direct quantities.*

### `DFTTBDMFTResults`

*This section has no direct quantities.*

### `DMFTMaxEntWorkflow`

*This section has no direct quantities.*

### `DMTMaxEntMethod`

*This section has no direct quantities.*

### `DMTMaxEntResults`

*This section has no direct quantities.*

### `XSWorkflow`

*This section has no direct quantities.*

### `XSMethod`

*This section has no direct quantities.*

### `XSResults`

*This section has no direct quantities.*


## Related Pages

- [Workflow Overview](../explanation/workflow/overview.md)
