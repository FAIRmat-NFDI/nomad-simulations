# Numerical Settings - Full Screen Diagram

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