# Thermodynamic Properties - Full Screen Diagram

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
    class Outputs {
    }
    class PhysicalProperty {
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
    class Variables {
    }
    class VirialTensor {
    }
    class Volume {
    }
    class Work {
    }
    PhysicalProperty <|-- BaseEnergy
    PhysicalProperty <|-- BaseForce
    BaseEnergy <|-- ChemicalPotential
    BaseEnergy <|-- Enthalpy
    PhysicalProperty <|-- Entropy
    BaseEnergy <|-- GibbsFreeEnergy
    BaseEnergy <|-- Heat
    PhysicalProperty <|-- HeatCapacity
    BaseEnergy <|-- HelmholtzFreeEnergy
    PhysicalProperty <|-- Hessian
    BaseEnergy <|-- InternalEnergy
    BaseEnergy <|-- KineticEnergy
    PhysicalProperty <|-- MassDensity
    BaseEnergy <|-- PotentialEnergy
    PhysicalProperty <|-- Pressure
    PhysicalProperty <|-- Temperature
    Variables <|-- Temperature
    BaseEnergy <|-- TotalEnergy
    BaseForce <|-- TotalForce
    BaseEnergy <|-- VirialTensor
    PhysicalProperty <|-- Volume
    BaseEnergy <|-- Work
    Outputs --> ChemicalPotential
    Outputs --> KineticEnergy : kinetic_energies
    Outputs --> PotentialEnergy : potential_energies
    Outputs --> Temperature
    Outputs --> TotalEnergy : total_energies
    Outputs --> TotalForce
    PhysicalProperty --> PhysicalProperty : contributions
    TotalEnergy --> BaseEnergy : contributions
    TotalForce --> BaseForce : contributions
```