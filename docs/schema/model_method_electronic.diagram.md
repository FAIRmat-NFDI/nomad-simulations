# Model Method Electronic - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes:

<div style="display:flex; align-items:center; gap:8px; margin:3px 0;"><svg width="56" height="16" aria-hidden="true"><line x1="48" y1="8" x2="18" y2="8" stroke="currentColor" stroke-width="1.8"/><polygon points="18,8 26,4 26,12" fill="white" stroke="currentColor" stroke-width="1.8"/></svg><code>Parent &lt;|-- Child</code> inheritance (Child extends Parent)</div>

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