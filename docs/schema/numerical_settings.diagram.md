# Numerical Settings - Full Screen Diagram

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
    class APWPlaneWaveBasisSet {
    }
    class AtomCenteredFunction {
    }
    class BasisSetComponent {
    }
    class ForceCalculations {
    }
    class KLinePath {
    }
    class KMesh {
    }
    class KSpace {
    }
    class Mesh {
    }
    class NumericalSettings {
    }
    class PlaneWaveBasisSet {
    }
    class SelfConsistency {
    }
    class Smearing {
    }
    PlaneWaveBasisSet <|-- APWPlaneWaveBasisSet
    NumericalSettings <|-- ForceCalculations
    Mesh <|-- KMesh
    NumericalSettings <|-- KSpace
    BasisSetComponent <|-- PlaneWaveBasisSet
    KMesh <|-- PlaneWaveBasisSet
    NumericalSettings <|-- SelfConsistency
    NumericalSettings <|-- Smearing
    KSpace --> KLinePath
    KSpace --> KMesh
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="50" y1="8" x2="22" y2="8"/><path class="uml-legend__head uml-legend__head--filled" d="M22 8 L32 3 L32 13 Z"/></svg><span><code>Parent &lt;|-- Child</code> is-a relationship, Parent-Child inheritance</span></div>
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="8" y1="8" x2="40" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M40 8 L48 4 M40 8 L48 12"/></svg><span><code>Owner --&gt; SubSection</code> has-a relationship, Owner-SubSection composition</span></div>
</div>

</div>
