# Numerical Settings - Full Screen Diagram

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
    AtomCenteredBasisSet --> AtomCenteredFunction : functional_compositions
    BaseGreensFunction --> KMesh
    BaseModelMethod --> NumericalSettings
    BasisSetContainer --> BasisSetComponent
    ElectronicBandStructure --> KLinePath : k_path
    KSpace --> KLinePath
    KSpace --> KMesh
    Permittivity --> KMesh : q_mesh
```