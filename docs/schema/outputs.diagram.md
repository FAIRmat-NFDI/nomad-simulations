# Outputs Base - Full Screen Diagram

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
    class AbsorptionSpectrum {
    }
    class ChemicalPotential {
    }
    class CrystalFieldSplitting {
    }
    class ElectronicDensityOfStates {
    }
    class ElectronicGreensFunction {
    }
    class ElectronicSelfEnergy {
    }
    class FermiSurface {
    }
    class Occupancy {
    }
    class Outputs {
    }
    class Permittivity {
    }
    class Temperature {
    }
    class TotalEnergy {
    }
    class XASSpectrum {
    }
    Outputs --> AbsorptionSpectrum : absorption_spectra
    Outputs --> ChemicalPotential
    Outputs --> CrystalFieldSplitting
    Outputs --> ElectronicDensityOfStates : electronic_dos
    Outputs --> ElectronicGreensFunction
    Outputs --> ElectronicSelfEnergy : electronic_self_energies
    Outputs --> FermiSurface
    Outputs --> Occupancy : occupancies
    Outputs --> Permittivity : permittivities
    Outputs --> Temperature
    Outputs --> TotalEnergy : total_energies
    Outputs --> XASSpectrum : xas_spectra
```

---


_Diagram 2 of 2 (split due to large number of children)_

```mermaid
classDiagram
    class ElectronicBandGap {
    }
    class ElectronicBandStructure {
    }
    class ElectronicEigenvalues {
    }
    class HoppingMatrix {
    }
    class HybridizationFunction {
    }
    class KineticEnergy {
    }
    class Outputs {
    }
    class PotentialEnergy {
    }
    class QuasiparticleWeight {
    }
    class TotalForce {
    }
    Outputs --> ElectronicBandGap
    Outputs --> ElectronicBandStructure
    Outputs --> ElectronicEigenvalues
    Outputs --> HoppingMatrix : hopping_matrices
    Outputs --> HybridizationFunction
    Outputs --> KineticEnergy : kinetic_energies
    Outputs --> PotentialEnergy : potential_energies
    Outputs --> QuasiparticleWeight
    Outputs --> TotalForce
```

<div style="font-size: 1em; color: #666; margin-top: 12px; margin-bottom: 12px;">
<b>Legend:</b>
<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="50" y1="15" x2="10" y2="15" stroke="currentColor" stroke-width="2.5"/><polygon points="10,15 20,8 20,22" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="miter"/></svg> inheritance ·
<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="10" y1="15" x2="50" y2="15" stroke="currentColor" stroke-width="2.5"/><polygon points="50,15 40,8 40,22" fill="currentColor"/></svg> containment ·
<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="10" y1="15" x2="50" y2="15" stroke="currentColor" stroke-width="2.5" stroke-dasharray="4,4"/><polygon points="50,15 40,8 40,22" fill="currentColor"/></svg> reference
</div>
