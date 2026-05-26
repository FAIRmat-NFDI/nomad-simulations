# Beyond-DFT Workflow Family - Full Screen Diagram

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
    class BeyondDFTMethod {
    }
    class BeyondDFTResults {
    }
    class BeyondDFTWorkflow {
    }
    class DFTGWMethod {
    }
    class DFTGWResults {
    }
    class DFTGWWorkflow {
    }
    class DFTTBDMFTMethod {
    }
    class DFTTBDMFTResults {
    }
    class DFTTBDMFTWorkflow {
    }
    class DFTTBMethod {
    }
    class DFTTBResults {
    }
    class DFTTBWorkflow {
    }
    class DMFTMaxEntWorkflow {
    }
    class DMTMaxEntMethod {
    }
    class DMTMaxEntResults {
    }
    class ElectronicStructureResults {
    }
    class SerialWorkflow {
    }
    class SimulationWorkflowMethod {
    }
    class SimulationWorkflowResults {
    }
    class WorkflowConvergenceResults {
    }
    class XSMethod {
    }
    class XSResults {
    }
    class XSWorkflow {
    }
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
    BeyondDFTWorkflow *-- BeyondDFTMethod : method
    BeyondDFTWorkflow *-- BeyondDFTResults : results
    DFTGWWorkflow *-- DFTGWMethod : method
    DFTGWWorkflow *-- DFTGWResults : results
    DFTTBDMFTWorkflow *-- DFTTBDMFTMethod : method
    DFTTBDMFTWorkflow *-- DFTTBDMFTResults : results
    DFTTBWorkflow *-- DFTTBMethod : method
    DFTTBWorkflow *-- DFTTBResults : results
    DMFTMaxEntWorkflow *-- DMTMaxEntMethod : method
    DMFTMaxEntWorkflow *-- DMTMaxEntResults : results
    SimulationWorkflowResults *-- WorkflowConvergenceResults : convergence
    XSWorkflow *-- XSMethod : method
    XSWorkflow *-- XSResults : results
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="54" y1="8" x2="22" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M10 8 L22 2 L22 14 Z"/></svg><span>inheritance (is-a)</span></div>
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><path class="uml-legend__head uml-legend__head--filled" d="M10 8 L16 2 L22 8 L16 14 Z"/><line class="uml-legend__line" x1="22" y1="8" x2="52" y2="8"/></svg><span>composition (has-a)</span></div>
</div>

</div>
