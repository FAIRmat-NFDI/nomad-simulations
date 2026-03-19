# Outputs - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes:

<div style="display:flex; align-items:center; gap:8px; margin:3px 0;"><svg width="56" height="16" aria-hidden="true"><line x1="48" y1="8" x2="18" y2="8" stroke="currentColor" stroke-width="1.8"/><polygon points="18,8 26,4 26,12" fill="white" stroke="currentColor" stroke-width="1.8"/></svg><code>Parent &lt;|-- Child</code> inheritance (Child extends Parent)</div>
<div style="display:flex; align-items:center; gap:8px; margin:3px 0;"><svg width="56" height="16" aria-hidden="true"><line x1="8" y1="8" x2="38" y2="8" stroke="currentColor" stroke-width="1.8"/><polygon points="46,8 38,4 38,12" fill="currentColor"/></svg><code>Owner --&gt; SubSection</code> containment/subsection</div>

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
    class Outputs {
    }
    class Permittivity {
    }
    class PhysicalProperty {
    }
    class PotentialEnergy {
    }
    class QuasiparticleWeight {
    }
    class SCFOutputs {
    }
    class Temperature {
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
    Outputs --> Permittivity : permittivities
    Outputs --> PotentialEnergy : potential_energies
    Outputs --> QuasiparticleWeight
    Outputs --> Temperature
    SCFOutputs --> Outputs : scf_steps
```

---


_Diagram 2 of 2 (split due to large number of children)_

```mermaid
classDiagram
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
    class PhysicalProperty {
    }
    class RadiusOfGyration {
    }
    class SCFOutputs {
    }
    class TotalEnergy {
    }
    class TotalForce {
    }
    class XASSpectrum {
    }
    Outputs <|-- SCFOutputs
    Outputs --> ElectronicSelfEnergy : electronic_self_energies
    Outputs --> FermiSurface
    Outputs --> HoppingMatrix : hopping_matrices
    Outputs --> HybridizationFunction
    Outputs --> KineticEnergy : kinetic_energies
    Outputs --> Occupancy : occupancies
    Outputs --> RadiusOfGyration : radii_of_gyration
    Outputs --> TotalEnergy : total_energies
    Outputs --> TotalForce
    Outputs --> XASSpectrum : xas_spectra
    SCFOutputs --> Outputs : scf_steps
```