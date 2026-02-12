# Outputs - Full Screen Diagram

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
    class AbsorptionSpectrum {
    }
    class ChemicalPotential {
    }
    class CrystalFieldSplitting {
    }
    class ElectronicDensityOfStates {
    }
    class FermiSurface {
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
    class QuasiparticleWeight {
    }
    class RadiusOfGyration {
    }
    class SCFOutputs {
    }
    class Temperature {
    }
    class TotalEnergy {
    }
    Outputs <|-- SCFOutputs
    Outputs --> AbsorptionSpectrum : absorption_spectra
    Outputs --> ChemicalPotential
    Outputs --> CrystalFieldSplitting
    Outputs --> ElectronicDensityOfStates : electronic_dos
    Outputs --> FermiSurface
    Outputs --> KineticEnergy : kinetic_energies
    Outputs --> Occupancy : occupancies
    Outputs --> Permittivity : permittivities
    Outputs --> QuasiparticleWeight
    Outputs --> RadiusOfGyration : radii_of_gyration
    Outputs --> Temperature
    Outputs --> TotalEnergy : total_energies
    SCFOutputs --> Outputs : scf_steps
    Outputs ..> PhysicalProperty : base type for most outputs
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
    class ElectronicGreensFunction {
    }
    class ElectronicSelfEnergy {
    }
    class HoppingMatrix {
    }
    class HybridizationFunction {
    }
    class Outputs {
    }
    class PhysicalProperty {
    }
    class PotentialEnergy {
    }
    class SCFOutputs {
    }
    class TotalForce {
    }
    class XASSpectrum {
    }
    Outputs <|-- SCFOutputs
    Outputs --> ElectronicBandGap
    Outputs --> ElectronicBandStructure
    Outputs --> ElectronicEigenvalues
    Outputs --> ElectronicGreensFunction
    Outputs --> ElectronicSelfEnergy : electronic_self_energies
    Outputs --> HoppingMatrix : hopping_matrices
    Outputs --> HybridizationFunction
    Outputs --> PotentialEnergy : potential_energies
    Outputs --> TotalForce
    Outputs --> XASSpectrum : xas_spectra
    SCFOutputs --> Outputs : scf_steps
    Outputs ..> PhysicalProperty : base type for most outputs
```