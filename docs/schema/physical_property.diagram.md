# Physical Property Backbone - Full Screen Diagram

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
    class BaseElectronicEigenvalues {
    }
    class BaseEnergy {
    }
    class BaseForce {
    }
    class BaseGreensFunction {
    }
    class Energy2 {
    }
    class ErrorEstimate {
    }
    class Frequency {
    }
    class ImaginaryTime {
    }
    class MatsubaraFrequency {
    }
    class PhysicalProperty {
    }
    class SpectralProfile {
    }
    class Time {
    }
    class WignerSeitz {
    }
    PhysicalProperty <|-- BaseElectronicEigenvalues
    PhysicalProperty <|-- BaseEnergy
    PhysicalProperty <|-- BaseForce
    PhysicalProperty <|-- BaseGreensFunction
    PhysicalProperty <|-- SpectralProfile
    BaseGreensFunction *-- Frequency : real_frequency
    BaseGreensFunction *-- ImaginaryTime
    BaseGreensFunction *-- MatsubaraFrequency
    BaseGreensFunction *-- Time
    BaseGreensFunction *-- WignerSeitz
    PhysicalProperty *-- ErrorEstimate : errors
    SpectralProfile *-- Energy2 : energies
    SpectralProfile *-- Energy2 : frequencies
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="54" y1="8" x2="28" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M18 8 L30 2 L30 14 Z"/></svg><span>inheritance (is-a)</span></div>
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><path class="uml-legend__head uml-legend__head--filled" d="M10 8 L16 2 L22 8 L16 14 Z"/><line class="uml-legend__line" x1="22" y1="8" x2="52" y2="8"/></svg><span>composition (has-a)</span></div>
</div>

</div>
