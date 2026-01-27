# Model Methods - Full Screen Diagram

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
    class BSE {
    }
    class BaseModelMethod {
    }
    class CoreHoleSpectra {
    }
    class DFT {
    }
    class DMFT {
    }
    class ExcitedStateMethodology {
    }
    class GW {
    }
    class ModelMethod {
    }
    class ModelMethodElectronic {
    }
    class NumericalSettings {
    }
    class Photon {
    }
    class Screening {
    }
    class Simulation {
    }
    class SlaterKoster {
    }
    class SlaterKosterBond {
    }
    class TB {
    }
    class Wannier {
    }
    class XCFunctional {
    }
    class xTB {
    }
    BaseModelMethod --> NumericalSettings
    DFT --> XCFunctional
    ModelMethod --> BaseModelMethod : contributions
    Simulation --> ModelMethod
    SlaterKoster --> SlaterKosterBond : bonds
    SlaterKoster --> SlaterKosterBond : overlaps
```