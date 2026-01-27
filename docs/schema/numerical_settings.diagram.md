# Numerical Settings - Full Screen Diagram

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
    class APWLChannel {
    }
    class APWPlaneWaveBasisSet {
    }
    class AtomCenteredBasisSet {
    }
    class AtomCenteredFunction {
    }
    class BaseGreensFunction {
    }
    class BaseModelMethod {
    }
    class BasisSetComponent {
    }
    class BasisSetContainer {
    }
    class EffectiveCorePotential {
    }
    class ElectronicBandStructure {
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
    class MuffinTinRegion {
    }
    class NumericalSettings {
    }
    class Permittivity {
    }
    class PlaneWaveBasisSet {
    }
    class SelfConsistency {
    }
    class Smearing {
    }
    class Variables {
    }
    BasisSetComponent <|-- APWLChannel
    PlaneWaveBasisSet <|-- APWPlaneWaveBasisSet
    BasisSetComponent <|-- AtomCenteredBasisSet
    NumericalSettings <|-- BasisSetContainer
    BasisSetComponent <|-- EffectiveCorePotential
    NumericalSettings <|-- ForceCalculations
    Variables <|-- KLinePath
    Mesh <|-- KMesh
    Variables <|-- KMesh
    NumericalSettings <|-- KSpace
    BasisSetComponent <|-- MuffinTinRegion
    Mesh <|-- MuffinTinRegion
    BasisSetComponent <|-- PlaneWaveBasisSet
    KMesh <|-- PlaneWaveBasisSet
    NumericalSettings <|-- SelfConsistency
    NumericalSettings <|-- Smearing
    AtomCenteredBasisSet --> AtomCenteredFunction : functional_compositions
    AtomCenteredBasisSet --> EffectiveCorePotential : ecps
    BaseGreensFunction --> KMesh
    BaseModelMethod --> NumericalSettings
    BasisSetContainer --> BasisSetComponent
    ElectronicBandStructure --> KLinePath : k_path
    KSpace --> KLinePath
    KSpace --> KMesh
    MuffinTinRegion --> APWLChannel : l_channels
    Permittivity --> KMesh : q_mesh
```