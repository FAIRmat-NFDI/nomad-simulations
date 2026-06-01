# Outputs - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes:

<div class="uml-diagram-card" markdown="1">

```mermaid
classDiagram
    class ChemicalPotential {
    }
    class ElectronicBandStructure {
    }
    class ElectronicDensityOfStates {
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
    class PhysicalProperty {
    }
    class PotentialEnergy {
    }
    class RadiusOfGyration {
    }
    class TotalEnergy {
    }
    class TotalForce {
    }
    class XASSpectrum {
    }
    Outputs *-- ChemicalPotential
    Outputs *-- ElectronicBandStructure
    Outputs *-- ElectronicDensityOfStates : electronic_dos
    Outputs *-- HybridizationFunction
    Outputs *-- KineticEnergy : kinetic_energies
    Outputs *-- Occupancy : occupancies
    Outputs *-- Permittivity : permittivities
    Outputs *-- PotentialEnergy : potential_energies
    Outputs *-- RadiusOfGyration : radii_of_gyration
    Outputs *-- TotalEnergy : total_energies
    Outputs *-- TotalForce
    Outputs *-- XASSpectrum : xas_spectra
```

</div>


---


_Diagram 2 of 2 (split due to large number of children)_

<div class="uml-diagram-card" markdown="1">

```mermaid
classDiagram
    class AbsorptionSpectrum {
    }
    class CrystalFieldSplitting {
    }
    class ElectronicBandGap {
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
    class Outputs {
    }
    class PhysicalProperty {
    }
    class QuasiparticleWeight {
    }
    class SCFSteps {
    }
    class Temperature {
    }
    Outputs *-- AbsorptionSpectrum : absorption_spectra
    Outputs *-- CrystalFieldSplitting
    Outputs *-- ElectronicBandGap
    Outputs *-- ElectronicEigenvalues
    Outputs *-- ElectronicGreensFunction
    Outputs *-- ElectronicSelfEnergy : electronic_self_energies
    Outputs *-- FermiSurface
    Outputs *-- HoppingMatrix : hopping_matrices
    Outputs *-- QuasiparticleWeight
    Outputs *-- SCFSteps
    Outputs *-- Temperature
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><path class="uml-legend__head uml-legend__head--filled" d="M10 8 L16 2 L22 8 L16 14 Z"/><line class="uml-legend__line" x1="22" y1="8" x2="52" y2="8"/></svg><span>composition (has-a)</span></div>
</div>

</div>
