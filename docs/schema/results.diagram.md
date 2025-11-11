# Results & Provenance - Full Screen Diagram

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
    class AbsorptionSpectrum {
    }
    class BeyondDFTResults {
    }
    class ChemicalPotential {
    }
    class CrystalFieldSplitting {
    }
    class DOSProfile {
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
    class ElectronicStructureResults {
    }
    class Energy2 {
    }
    class FermiSurface {
    }
    class GeometryOptimizationResults {
    }
    class HoppingMatrix {
    }
    class HybridizationFunction {
    }
    class KLinePath {
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
    class Simulation {
    }
    class Temperature {
    }
    class ThermodynamicsResults {
    }
    class TotalEnergy {
    }
    class TotalForce {
    }
    class TrajectoryOutputs {
    }
    class XASSpectrum {
    }
    BeyondDFTResults --> ElectronicStructureResults : dft
    BeyondDFTResults --> ElectronicStructureResults : ext
    DOSProfile --> Energy2 : energies
    ElectronicBandStructure --> KLinePath : k_path
    ElectronicDensityOfStates --> DOSProfile : projected_dos
    ElectronicDensityOfStates --> Energy2 : energies
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
    Simulation --> Outputs
    XASSpectrum --> AbsorptionSpectrum : exafs_spectrum
    XASSpectrum --> AbsorptionSpectrum : xanes_spectrum
```