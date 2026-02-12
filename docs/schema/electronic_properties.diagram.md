# Electronic Structure Properties - Full Screen Diagram

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
    class Occupancy {
    }
    ElectronicEigenvalues <|-- ElectronicBandStructure
    DOSProfile <|-- ElectronicDensityOfStates
    BaseElectronicEigenvalues <|-- ElectronicEigenvalues
    DOSProfile --> Energy2 : energies
    ElectronicDensityOfStates --> DOSProfile : projected_dos
    ElectronicDensityOfStates --> Energy2 : energies
    ElectronicEigenvalues --> BaseElectronicEigenvalues : contributions
```