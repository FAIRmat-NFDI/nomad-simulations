# Thermodynamic Properties - Full Screen Diagram

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
    Outputs --> ChemicalPotential
    Outputs --> KineticEnergy : kinetic_energies
    Outputs --> PotentialEnergy : potential_energies
    Outputs --> Temperature
    Outputs --> TotalEnergy : total_energies
    Outputs --> TotalForce
    TotalEnergy --> BaseEnergy : contributions
    TotalForce --> BaseForce : contributions
```