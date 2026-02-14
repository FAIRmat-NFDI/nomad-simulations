# Many-Body Properties - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes:

<div style="display:flex; align-items:center; gap:8px; margin:3px 0;"><svg width="56" height="16" aria-hidden="true"><line x1="48" y1="8" x2="18" y2="8" stroke="currentColor" stroke-width="1.8"/><polygon points="18,8 26,4 26,12" fill="white" stroke="currentColor" stroke-width="1.8"/></svg><code>Parent &lt;|-- Child</code> inheritance (Child extends Parent)</div>
<div style="display:flex; align-items:center; gap:8px; margin:3px 0;"><svg width="56" height="16" aria-hidden="true"><line x1="8" y1="8" x2="38" y2="8" stroke="currentColor" stroke-width="1.8"/><polygon points="46,8 38,4 38,12" fill="currentColor"/></svg><code>Owner --&gt; SubSection</code> containment/subsection</div>

```mermaid
classDiagram
    class BaseGreensFunction {
    }
    class CrystalFieldSplitting {
    }
    class ElectronicGreensFunction {
    }
    class ElectronicSelfEnergy {
    }
    class Frequency {
    }
    class HoppingMatrix {
    }
    class HybridizationFunction {
    }
    class ImaginaryTime {
    }
    class MatsubaraFrequency {
    }
    class QuasiparticleWeight {
    }
    class Time {
    }
    class WignerSeitz {
    }
    BaseGreensFunction <|-- ElectronicGreensFunction
    BaseGreensFunction <|-- ElectronicSelfEnergy
    BaseGreensFunction <|-- HybridizationFunction
    BaseGreensFunction --> Frequency : real_frequency
    BaseGreensFunction --> ImaginaryTime
    BaseGreensFunction --> MatsubaraFrequency
    BaseGreensFunction --> Time
    BaseGreensFunction --> WignerSeitz
```