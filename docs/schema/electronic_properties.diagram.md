# Electronic Structure Properties - Full Screen Diagram

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
    class BaseElectronicEigenvalues {
    }
    class DOSProfile {
    }
    class ElectronicBandGap {
    }
    class ElectronicBandStructure {
    }
    class ElectronicDensityOfStates {
    }
    class ElectronicEigenvalues {
    }
    class Energy2 {
    }
    class FermiSurface {
    }
    class KLinePath {
    }
    class Occupancy {
    }
    class Outputs {
    }
    class PhysicalProperty {
    }
    class SpectralProfile {
    }
    PhysicalProperty <|-- BaseElectronicEigenvalues
    SpectralProfile <|-- DOSProfile
    PhysicalProperty <|-- ElectronicBandGap
    ElectronicEigenvalues <|-- ElectronicBandStructure
    DOSProfile <|-- ElectronicDensityOfStates
    BaseElectronicEigenvalues <|-- ElectronicEigenvalues
    PhysicalProperty <|-- FermiSurface
    PhysicalProperty <|-- Occupancy
    PhysicalProperty <|-- SpectralProfile
    DOSProfile --> Energy2 : energies
    ElectronicBandStructure --> KLinePath : k_path
    ElectronicDensityOfStates --> DOSProfile : projected_dos
    ElectronicDensityOfStates --> Energy2 : energies
    ElectronicEigenvalues --> BaseElectronicEigenvalues : value_contributions
    Outputs --> ElectronicBandGap
    Outputs --> ElectronicBandStructure
    Outputs --> ElectronicDensityOfStates : electronic_dos
    Outputs --> ElectronicEigenvalues
    Outputs --> FermiSurface
    Outputs --> Occupancy : occupancies
    PhysicalProperty --> PhysicalProperty : contributions
    SpectralProfile --> Energy2 : energies
    SpectralProfile --> Energy2 : frequencies
```