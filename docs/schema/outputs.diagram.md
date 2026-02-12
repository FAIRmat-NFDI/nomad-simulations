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
    class CrystalFieldSplitting {
    }
    class ElectronicBandStructure {
    }
    class ElectronicDensityOfStates {
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
    class Permittivity {
    }
    class PhysicalProperty {
    }
    class PotentialEnergy {
    }
    class SCFOutputs {
    }
    class Temperature {
    }
    class TotalForce {
    }
    class XASSpectrum {
    }
    Outputs <|-- SCFOutputs
    Outputs --> CrystalFieldSplitting
    Outputs --> ElectronicBandStructure
    Outputs --> ElectronicDensityOfStates : electronic_dos
    Outputs --> ElectronicGreensFunction
    Outputs --> ElectronicSelfEnergy : electronic_self_energies
    Outputs --> HoppingMatrix : hopping_matrices
    Outputs --> HybridizationFunction
    Outputs --> Permittivity : permittivities
    Outputs --> PotentialEnergy : potential_energies
    Outputs --> Temperature
    Outputs --> TotalForce
    Outputs --> XASSpectrum : xas_spectra
    SCFOutputs --> Outputs : scf_steps
    Outputs ..> PhysicalProperty : base type for most outputs
```

---


_Diagram 2 of 2 (split due to large number of children)_

```mermaid
classDiagram
    class AbsorptionSpectrum {
    }
    class ChemicalPotential {
    }
    class ElectronicBandGap {
    }
    class ElectronicEigenvalues {
    }
    class FermiSurface {
    }
    class KineticEnergy {
    }
    class Occupancy {
    }
    class Outputs {
    }
    class PhysicalProperty {
    }
    class QuasiparticleWeight {
    }
    class RadiusOfGyration {
    }
    class SCFOutputs {
    }
    class TotalEnergy {
    }
    Outputs <|-- SCFOutputs
    Outputs --> AbsorptionSpectrum : absorption_spectra
    Outputs --> ChemicalPotential
    Outputs --> ElectronicBandGap
    Outputs --> ElectronicEigenvalues
    Outputs --> FermiSurface
    Outputs --> KineticEnergy : kinetic_energies
    Outputs --> Occupancy : occupancies
    Outputs --> QuasiparticleWeight
    Outputs --> RadiusOfGyration : radii_of_gyration
    Outputs --> TotalEnergy : total_energies
    SCFOutputs --> Outputs : scf_steps
    Outputs ..> PhysicalProperty : base type for most outputs
```