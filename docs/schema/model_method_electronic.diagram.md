# Model Method Electronic - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes:

- `Owner --> SubSection`: containment/subsection relationship
- `Source ..> Target`: typed reference from one section to another
- `Parent <|-- Child`: inheritance (`Child` extends `Parent`)

```mermaid
classDiagram
    class BSE {
    }
    class ConfigurationInteraction {
    }
    class CoreHoleSpectra {
    }
    class CoupledCluster {
    }
    class DFT {
    }
    class DMFT {
    }
    class ExcitedStateMethodology {
    }
    class GW {
    }
    class HartreeFock {
    }
    class ModelMethodElectronic {
    }
    class PerturbationMethod {
    }
    class Screening {
    }
    class SlaterKoster {
    }
    class TB {
    }
    class TDDFT {
    }
    class Wannier {
    }
    class xTB {
    }
    ExcitedStateMethodology <|-- BSE
    ModelMethodElectronic <|-- ConfigurationInteraction
    ModelMethodElectronic <|-- CoreHoleSpectra
    ModelMethodElectronic <|-- CoupledCluster
    ModelMethodElectronic <|-- DFT
    ModelMethodElectronic <|-- DMFT
    ModelMethodElectronic <|-- ExcitedStateMethodology
    ExcitedStateMethodology <|-- GW
    ModelMethodElectronic <|-- HartreeFock
    ModelMethodElectronic <|-- PerturbationMethod
    ExcitedStateMethodology <|-- Screening
    TB <|-- SlaterKoster
    ModelMethodElectronic <|-- TB
    ExcitedStateMethodology <|-- TDDFT
    TB <|-- Wannier
    TB <|-- xTB
```