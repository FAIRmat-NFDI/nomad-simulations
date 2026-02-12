# Thermodynamic Properties - Full Screen Diagram

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
    class BaseEnergy {
    }
    class BaseForce {
    }
    class ChemicalPotential {
    }
    class Enthalpy {
    }
    class Entropy {
    }
    class GibbsFreeEnergy {
    }
    class Heat {
    }
    class HeatCapacity {
    }
    class HelmholtzFreeEnergy {
    }
    class Hessian {
    }
    class InternalEnergy {
    }
    class KineticEnergy {
    }
    class MassDensity {
    }
    class PotentialEnergy {
    }
    class Pressure {
    }
    class Temperature {
    }
    class TotalEnergy {
    }
    class TotalForce {
    }
    class VirialTensor {
    }
    class Volume {
    }
    class Work {
    }
    BaseEnergy <|-- ChemicalPotential
    BaseEnergy <|-- Enthalpy
    BaseEnergy <|-- GibbsFreeEnergy
    BaseEnergy <|-- Heat
    BaseEnergy <|-- HelmholtzFreeEnergy
    BaseEnergy <|-- InternalEnergy
    BaseEnergy <|-- KineticEnergy
    BaseEnergy <|-- PotentialEnergy
    BaseEnergy <|-- TotalEnergy
    BaseForce <|-- TotalForce
    BaseEnergy <|-- VirialTensor
    BaseEnergy <|-- Work
    TotalEnergy --> BaseEnergy : contributions
    TotalForce --> BaseForce : contributions
```