# Model Methods - Full Screen Diagram

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
    class ForceField {
    }
    class GW {
    }
    class ModelMethod {
    }
    class ModelMethodElectronic {
    }
    class NumericalSettings {
    }
    class Potential {
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
    ExcitedStateMethodology <|-- BSE
    ModelMethodElectronic <|-- CoreHoleSpectra
    ModelMethodElectronic <|-- DFT
    ModelMethodElectronic <|-- DMFT
    ModelMethodElectronic <|-- ExcitedStateMethodology
    ModelMethod <|-- ForceField
    ExcitedStateMethodology <|-- GW
    BaseModelMethod <|-- ModelMethod
    ModelMethod <|-- ModelMethodElectronic
    BaseModelMethod <|-- Potential
    ExcitedStateMethodology <|-- Screening
    TB <|-- SlaterKoster
    ModelMethodElectronic <|-- TB
    TB <|-- Wannier
    TB <|-- xTB
    BaseModelMethod --> NumericalSettings
    DFT --> XCFunctional
    ForceField --> Potential : contributions
    ModelMethod --> BaseModelMethod : contributions
    Simulation --> ModelMethod
    SlaterKoster --> SlaterKosterBond : bonds
    SlaterKoster --> SlaterKosterBond : overlaps
```

---

```mermaid
classDiagram
    class Photon {
    }
```