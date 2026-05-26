# Model Method Electronic - Full Screen Diagram

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
    class ADC {
    }
    class BSE {
    }
    class CC {
    }
    class CI {
    }
    class CoreHoleSpectra {
    }
    class DFT {
    }
    class DMFT {
    }
    class EOMCC {
    }
    class ElectronicResponseMethod {
    }
    class ExcitedStateMethodology {
    }
    class GW {
    }
    class HF {
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
    ElectronicResponseMethod <|-- ADC
    ExcitedStateMethodology <|-- BSE
    ModelMethodElectronic <|-- CC
    ModelMethodElectronic <|-- CI
    ModelMethodElectronic <|-- CoreHoleSpectra
    ModelMethodElectronic <|-- DFT
    ElectronicResponseMethod <|-- DMFT
    ElectronicResponseMethod <|-- EOMCC
    ModelMethodElectronic <|-- ElectronicResponseMethod
    ElectronicResponseMethod <|-- ExcitedStateMethodology
    ExcitedStateMethodology <|-- GW
    ModelMethodElectronic <|-- HF
    ModelMethodElectronic <|-- PerturbationMethod
    ExcitedStateMethodology <|-- Screening
    TB <|-- SlaterKoster
    ModelMethodElectronic <|-- TB
    ExcitedStateMethodology <|-- TDDFT
    TB <|-- Wannier
    TB <|-- xTB
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="54" y1="8" x2="22" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M10 8 L22 2 L22 14 Z"/></svg><span>inheritance (is-a)</span></div>
</div>

</div>
