# Many-Body Properties - Full Screen Diagram

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
    class KMesh {
    }
    class MatsubaraFrequency {
    }
    class Outputs {
    }
    class PhysicalProperty {
    }
    class QuasiparticleWeight {
    }
    class Time {
    }
    class WignerSeitz {
    }
    PhysicalProperty <|-- BaseGreensFunction
    PhysicalProperty <|-- CrystalFieldSplitting
    BaseGreensFunction <|-- ElectronicGreensFunction
    BaseGreensFunction <|-- ElectronicSelfEnergy
    PhysicalProperty <|-- HoppingMatrix
    BaseGreensFunction <|-- HybridizationFunction
    Time <|-- Outputs
    PhysicalProperty <|-- QuasiparticleWeight
    BaseGreensFunction --> Frequency : real_frequency
    BaseGreensFunction --> ImaginaryTime
    BaseGreensFunction --> KMesh
    BaseGreensFunction --> MatsubaraFrequency
    BaseGreensFunction --> Time
    BaseGreensFunction --> WignerSeitz
    Outputs --> CrystalFieldSplitting
    Outputs --> ElectronicGreensFunction
    Outputs --> ElectronicSelfEnergy : electronic_self_energies
    Outputs --> HoppingMatrix : hopping_matrices
    Outputs --> HybridizationFunction
    Outputs --> QuasiparticleWeight
    PhysicalProperty --> PhysicalProperty : contributions
```