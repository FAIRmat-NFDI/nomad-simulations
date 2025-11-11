# Methods & Parameters - Full Screen Diagram

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
    class BaseModelMethod {
    }
    class BaseSimulation {
    }
    class DFT {
    }
    class DMFT {
    }
    class GW {
    }
    class ModelMethod {
    }
    class ModelMethodElectronic {
    }
    class NumericalSettings {
    }
    class Program {
    }
    class Simulation {
    }
    class Smearing {
    }
    class TB {
    }
    class XCFunctional {
    }
    BaseModelMethod --> NumericalSettings
    BaseSimulation --> Program
    DFT --> XCFunctional
    ModelMethod --> BaseModelMethod : contributions
    Simulation --> ModelMethod
```