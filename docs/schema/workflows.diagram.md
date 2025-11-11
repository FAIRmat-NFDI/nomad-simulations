# Workflows - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes in this vertical:

- **Solid arrows** (-->) represent SubSection containment
- **Dashed arrows** (..->) represent Quantity references

```mermaid
classDiagram
    class GeometryOptimization {
    }
    class MolecularDynamics {
    }
    class ParallelWorkflow {
    }
    class SelfConsistency {
    }
    class SerialWorkflow {
    }
    class SimulationTask {
    }
    class SimulationWorkflow {
    }
    class SimulationWorkflowModel {
    }
    class SimulationWorkflowResults {
    }
    class SinglePoint {
    }
    class Task {
    }
    class Workflow {
    }
    SimulationWorkflow --> SimulationWorkflowModel : model
    SimulationWorkflow --> SimulationWorkflowResults : results
```