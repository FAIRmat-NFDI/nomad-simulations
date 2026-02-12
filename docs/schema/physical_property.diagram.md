# Physical Property Backbone - Full Screen Diagram

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
    BaseGreensFunction --> Frequency : real_frequency
    BaseGreensFunction --> ImaginaryTime
    BaseGreensFunction --> MatsubaraFrequency
    BaseGreensFunction --> Time
    BaseGreensFunction --> WignerSeitz
    PhysicalProperty --> ErrorEstimate : errors
    SpectralProfile --> Energy2 : energies
    SpectralProfile --> Energy2 : frequencies
```