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
    class ElectronicBandGap {
    }
    class ElectronicBandStructure {
    }
    class ElectronicDensityOfStates {
    }
    class ElectronicEigenvalues {
    }
    class ElectronicGreensFunction {
    }
    class ElectronicSelfEnergy {
    }
    class FermiSurface {
    }
    class HoppingMatrix {
    }
    class HybridizationFunction {
    }
    class KineticEnergy {
    }
    class Occupancy {
    }
    class Outputs {
    }
    class Permittivity {
    }
    class PotentialEnergy {
    }
    class QuasiparticleWeight {
    }
    class SCFOutputs {
    }
    class Temperature {
    }
    class TotalEnergy {
    }
    class TotalForce {
    }
    class XASSpectrum {
    }
    Outputs <|-- SCFOutputs
    Outputs --> AbsorptionSpectrum : absorption_spectra
    Outputs --> ChemicalPotential
    Outputs --> CrystalFieldSplitting
    Outputs --> ElectronicBandGap
    Outputs --> ElectronicBandStructure
    Outputs --> ElectronicDensityOfStates : electronic_dos
    Outputs --> ElectronicEigenvalues
    Outputs --> ElectronicGreensFunction
    Outputs --> ElectronicSelfEnergy : electronic_self_energies
    Outputs --> FermiSurface
    Outputs --> HoppingMatrix : hopping_matrices
    Outputs --> HybridizationFunction
    Outputs --> KineticEnergy : kinetic_energies
    Outputs --> Occupancy : occupancies
    Outputs --> Permittivity : permittivities
    Outputs --> PotentialEnergy : potential_energies
    Outputs --> QuasiparticleWeight
    Outputs --> Temperature
    Outputs --> TotalEnergy : total_energies
    Outputs --> TotalForce
    Outputs --> XASSpectrum : xas_spectra
    SCFOutputs --> Outputs : scf_steps
```

<div style="font-size: 1em; color: #666; margin-top: 12px; margin-bottom: 12px;">
<b>Legend:</b>
<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="50" y1="15" x2="10" y2="15" stroke="currentColor" stroke-width="2.5"/><polygon points="10,15 20,8 20,22" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="miter"/></svg> inheritance ·
<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="10" y1="15" x2="50" y2="15" stroke="currentColor" stroke-width="2.5"/><polygon points="50,15 40,8 40,22" fill="currentColor"/></svg> containment ·
<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="10" y1="15" x2="50" y2="15" stroke="currentColor" stroke-width="2.5" stroke-dasharray="4,4"/><polygon points="50,15 40,8 40,22" fill="currentColor"/></svg> reference
</div>


---

```mermaid
classDiagram
    class PhysicalProperty {
    }
    PhysicalProperty --> PhysicalProperty : contributions
```

<div style="font-size: 1em; color: #666; margin-top: 12px; margin-bottom: 12px;">
<b>Legend:</b>
<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="50" y1="15" x2="10" y2="15" stroke="currentColor" stroke-width="2.5"/><polygon points="10,15 20,8 20,22" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="miter"/></svg> inheritance ·
<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="10" y1="15" x2="50" y2="15" stroke="currentColor" stroke-width="2.5"/><polygon points="50,15 40,8 40,22" fill="currentColor"/></svg> containment ·
<svg width="60" height="30" style="vertical-align: middle; margin: 0 6px;"><line x1="10" y1="15" x2="50" y2="15" stroke="currentColor" stroke-width="2.5" stroke-dasharray="4,4"/><polygon points="50,15 40,8 40,22" fill="currentColor"/></svg> reference
</div>
