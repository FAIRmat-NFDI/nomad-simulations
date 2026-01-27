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
    class BaseElectronicEigenvalues {
    }
    class BaseEnergy {
    }
    class BaseForce {
    }
    class BaseGreensFunction {
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
    class Entropy {
    }
    class FermiSurface {
    }
    class HeatCapacity {
    }
    class Hessian {
    }
    class HoppingMatrix {
    }
    class HybridizationFunction {
    }
    class KineticEnergy {
    }
    class MassDensity {
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
    class Pressure {
    }
    class QuasiparticleWeight {
    }
    class SCFOutputs {
    }
    class Simulation {
    }
    class SpectralProfile {
    }
    class Temperature {
    }
    class Time {
    }
    class TotalEnergy {
    }
    class TotalForce {
    }
    class Volume {
    }
    class WorkflowOutputs {
    }
    class XASSpectrum {
    }
    SpectralProfile <|-- AbsorptionSpectrum
    PhysicalProperty <|-- BaseElectronicEigenvalues
    PhysicalProperty <|-- BaseEnergy
    PhysicalProperty <|-- BaseForce
    PhysicalProperty <|-- BaseGreensFunction
    BaseEnergy <|-- ChemicalPotential
    PhysicalProperty <|-- CrystalFieldSplitting
    PhysicalProperty <|-- ElectronicBandGap
    ElectronicEigenvalues <|-- ElectronicBandStructure
    BaseElectronicEigenvalues <|-- ElectronicEigenvalues
    BaseGreensFunction <|-- ElectronicGreensFunction
    BaseGreensFunction <|-- ElectronicSelfEnergy
    PhysicalProperty <|-- Entropy
    PhysicalProperty <|-- FermiSurface
    PhysicalProperty <|-- HeatCapacity
    PhysicalProperty <|-- Hessian
    PhysicalProperty <|-- HoppingMatrix
    BaseGreensFunction <|-- HybridizationFunction
    BaseEnergy <|-- KineticEnergy
    PhysicalProperty <|-- MassDensity
    PhysicalProperty <|-- Occupancy
    Time <|-- Outputs
    PhysicalProperty <|-- Permittivity
    BaseEnergy <|-- PotentialEnergy
    PhysicalProperty <|-- Pressure
    PhysicalProperty <|-- QuasiparticleWeight
    Outputs <|-- SCFOutputs
    PhysicalProperty <|-- SpectralProfile
    PhysicalProperty <|-- Temperature
    BaseEnergy <|-- TotalEnergy
    BaseForce <|-- TotalForce
    PhysicalProperty <|-- Volume
    Outputs <|-- WorkflowOutputs
    AbsorptionSpectrum <|-- XASSpectrum
    BaseGreensFunction --> Time
    ElectronicEigenvalues --> BaseElectronicEigenvalues : value_contributions
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
    PhysicalProperty --> PhysicalProperty : contributions
    SCFOutputs --> Outputs : scf_steps
    Simulation --> Outputs
    TotalEnergy --> BaseEnergy : contributions
    TotalForce --> BaseForce : contributions
    XASSpectrum --> AbsorptionSpectrum : exafs_spectrum
    XASSpectrum --> AbsorptionSpectrum : xanes_spectrum
```