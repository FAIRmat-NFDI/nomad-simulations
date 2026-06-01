# Beyond-HF Workflow Family - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes:

<div class="uml-diagram-card" markdown="1">

```mermaid
classDiagram
    class BeyondHFMethod
    class BeyondHFResults
    class BeyondHFWorkflow
    class ElectronicStructureResults
    class HFCCMethod
    class HFCCResults
    class HFCCWorkflow
    class HFCIMethod
    class HFCIResults
    class HFCIWorkflow
    class HFLocalCCMethod
    class HFLocalCCResults
    class HFLocalCCWorkflow
    class LocalCCWorkflow
    class LocalCCWorkflowMethod
    class LocalCCWorkflowResults
    class OrbitalLocalization
    class SerialWorkflow
    class SimulationWorkflowMethod
    class SimulationWorkflowResults
    class WorkflowConvergenceResults
    SimulationWorkflowMethod <|-- BeyondHFMethod
    SimulationWorkflowResults <|-- BeyondHFResults
    SerialWorkflow <|-- BeyondHFWorkflow
    SimulationWorkflowResults <|-- ElectronicStructureResults
    BeyondHFMethod <|-- HFCCMethod
    BeyondHFResults <|-- HFCCResults
    BeyondHFWorkflow <|-- HFCCWorkflow
    BeyondHFMethod <|-- HFCIMethod
    BeyondHFResults <|-- HFCIResults
    BeyondHFWorkflow <|-- HFCIWorkflow
    BeyondHFResults *-- ElectronicStructureResults : ext
    BeyondHFResults *-- ElectronicStructureResults : hf
    BeyondHFWorkflow *-- BeyondHFMethod : method
    BeyondHFWorkflow *-- BeyondHFResults : results
    HFCCWorkflow *-- HFCCMethod : method
    HFCCWorkflow *-- HFCCResults : results
    HFCIWorkflow *-- HFCIMethod : method
    HFCIWorkflow *-- HFCIResults : results
    SimulationWorkflowMethod <|-- LocalCCWorkflowMethod
    SimulationWorkflowResults <|-- LocalCCWorkflowResults
    SerialWorkflow <|-- LocalCCWorkflow
    LocalCCWorkflowMethod <|-- HFLocalCCMethod
    LocalCCWorkflowResults <|-- HFLocalCCResults
    LocalCCWorkflow <|-- HFLocalCCWorkflow
    LocalCCWorkflowMethod *-- OrbitalLocalization : orbital_localization
    HFLocalCCResults *-- ElectronicStructureResults : ext
    HFLocalCCResults *-- ElectronicStructureResults : hf
    HFLocalCCWorkflow *-- HFLocalCCMethod : method
    HFLocalCCWorkflow *-- HFLocalCCResults : results
    SimulationWorkflowResults *-- WorkflowConvergenceResults : convergence
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="54" y1="8" x2="22" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M10 8 L22 2 L22 14 Z"/></svg><span>inheritance (is-a)</span></div>
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><path class="uml-legend__head uml-legend__head--filled" d="M10 8 L16 2 L22 8 L16 14 Z"/><line class="uml-legend__line" x1="22" y1="8" x2="52" y2="8"/></svg><span>composition (has-a)</span></div>
</div>

</div>
