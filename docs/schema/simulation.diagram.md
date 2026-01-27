# Simulation Entry - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes:

- **Solid arrows** (-->) represent SubSection containment
- **Dashed arrows** (..->) represent Quantity references
- **Inheritance arrows** (<|--) represent class inheritance

```mermaid
classDiagram
    class BaseSimulation {
    }
    class ModelMethod {
    }
    class ModelSystem {
    }
    class Outputs {
    }
    class Program {
    }
    class Simulation {
    }
    class Time {
    }
    Time <|-- BaseSimulation
    Time <|-- Outputs
    BaseSimulation <|-- Simulation
    BaseSimulation --> Program
    ModelSystem --> ModelSystem : sub_systems
    Simulation --> ModelMethod
    Simulation --> ModelSystem
    Simulation --> Outputs
```