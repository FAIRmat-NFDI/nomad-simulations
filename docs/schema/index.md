# Schema Documentation

This section contains auto-generated documentation for the NOMAD simulations schema.

The schema is organized into vertical domains, each covering a specific aspect of simulation metadata:

## [Simulation Entry](simulation.md)

Root entry point for simulations: Simulation, BaseSimulation, and Program

**In scope:** Root Simulation section that contains all simulation metadata, Timing information (cpu1_start, cpu1_end, wall_start, wall_end), Program details (name, version, link), Entry point that references the four main subsections

**Key sections:** Simulation, BaseSimulation, Program

## [Model System](model_system.md)

Complete ModelSystem tree: geometric spaces, cells, symmetry, and particle organization

**In scope:** ModelSystem as the root of the system tree, Geometric spaces: Cell and AtomicCell with lattice vectors, Symmetry information: space groups, point groups, Bravais lattices, Chemical formulas: descriptive, reduced, IUPAC, Hill, anonymous, Particle states: AtomsState for atoms, CGBeadState for coarse-grained beads, Recursive sub_systems containment (ModelSystem contains ModelSystem), Positions, velocities, particle_indices, System type and dimensionality

**Key sections:** ModelSystem, GeometricSpace, Cell, AtomicCell, Symmetry, ChemicalFormula, ParticleState, AtomsState, CGBeadState

## [Atomic State Properties](atoms_state.md)

Detailed atomic-level properties within AtomsState: orbitals, core holes, and Hubbard interactions

**In scope:** AtomsState as the container for atomic property details, OrbitalsState: quantum numbers (n, l, ml, j, mj, ms), Orbital degeneracy and occupation, CoreHole: excited electron states for spectroscopy, HubbardInteractions: U matrix, U_effective, J_Hunds for correlated systems, Slater integrals for many-body interactions

**Key sections:** AtomsState, OrbitalsState, CoreHole, HubbardInteractions

## [Model Methods](model_method.md)

Complete ModelMethod tree: electronic structure methods and their hierarchy

**In scope:** Method inheritance hierarchy: BaseModelMethod → ModelMethod → ModelMethodElectronic, DFT: Jacobs ladder, XC functionals, exact exchange, van der Waals, Tight-binding (TB): DFTB, xTB, Wannier, Slater-Koster, Excited states: ExcitedStateMethodology → GW, BSE, Screening for many-body methods, CoreHoleSpectra for X-ray spectroscopy, DMFT for strongly correlated systems, Method contributions and references between methods

**Key sections:** BaseModelMethod, ModelMethod, ModelMethodElectronic, DFT, XCFunctional, TB, Wannier, SlaterKoster, SlaterKosterBond, xTB, ExcitedStateMethodology, Screening, GW, BSE, CoreHoleSpectra, Photon, DMFT

## [Numerical Settings](numerical_settings.md)

Computational parameters: meshes, basis sets, convergence, and discretization

**In scope:** K-point meshes and line paths for band structures, Real-space meshes and grids, Basis set specifications: plane-wave, APW, atom-centered, Convergence thresholds and maximum iterations, Smearing functions: Fermi-Dirac, Gaussian, Methfessel-Paxton, Force calculation settings

**Key sections:** NumericalSettings, Mesh, KMesh, KLinePath, KSpace, Smearing, SelfConsistency, ForceCalculations, BasisSetComponent, PlaneWaveBasisSet, APWPlaneWaveBasisSet, AtomCenteredFunction

## [Outputs Base](outputs.md)

Base output structure and common property definitions

**In scope:** Outputs section that references ModelSystem and ModelMethod, SCFOutputs with scf_steps for iteration history, PhysicalProperty base class for all computed properties, Property contributions and derivations, SCF convergence checking

**Key sections:** Outputs, SCFOutputs, PhysicalProperty

## [Electronic Structure Properties](electronic_properties.md)

Electronic eigenvalues, band structures, DOS, band gaps, occupancies, and Fermi surfaces

**In scope:** Eigenvalue hierarchy: BaseElectronicEigenvalues → ElectronicEigenvalues → ElectronicBandStructure, Band structures along high-symmetry paths, Density of states (DOS) profiles, Electronic band gaps (direct, indirect), Orbital occupancies, Fermi surface topology

**Key sections:** BaseElectronicEigenvalues, ElectronicEigenvalues, ElectronicBandStructure, ElectronicBandGap, DOSProfile, ElectronicDensityOfStates, Occupancy, FermiSurface

## [Many-Body Properties](manybody_properties.md)

Green's functions, self-energies, hybridization, quasiparticle weights, hopping matrices

**In scope:** Green's function base class and electronic specialization, Self-energies from GW and DMFT, Hybridization functions for impurity problems, Quasiparticle renormalization weights, Hopping matrices from tight-binding, Crystal field splittings in correlated systems

**Key sections:** BaseGreensFunction, ElectronicGreensFunction, ElectronicSelfEnergy, HybridizationFunction, QuasiparticleWeight, HoppingMatrix, CrystalFieldSplitting

## [Spectroscopic Properties](spectroscopy.md)

Absorption spectra, XAS, and dielectric response

**In scope:** Spectral profile base class, Absorption spectra from BSE calculations, X-ray absorption spectra (XAS) from core hole calculations, Frequency-dependent dielectric functions (permittivity)

**Key sections:** SpectralProfile, AbsorptionSpectrum, XASSpectrum, Permittivity

## [Thermodynamic Properties](thermodynamics.md)

Energies, forces, pressure, temperature, and thermodynamic state functions

**In scope:** Energy hierarchy: BaseEnergy → specific energy types, Free energies: Gibbs, Helmholtz, Force hierarchy: BaseForce → TotalForce, Thermodynamic state variables: pressure, volume, temperature, Entropy and heat capacities, Virial tensor for stress calculations, Hessian matrices for phonon calculations

**Key sections:** BaseEnergy, TotalEnergy, KineticEnergy, PotentialEnergy, Heat, Work, InternalEnergy, Enthalpy, GibbsFreeEnergy, HelmholtzFreeEnergy, ChemicalPotential, VirialTensor, BaseForce, TotalForce, Pressure, Volume, Temperature, Entropy, HeatCapacity, MassDensity, Hessian


---

## How to use this documentation

Each vertical page contains:

- **Purpose**: High-level description of what the vertical covers
- **Relationship map**: Mermaid diagram showing connections between sections
- **Key sections**: Table linking to detailed class definitions in the MetaInfo browser
- **Micro-examples**: Sample YAML snippets demonstrating structure

For detailed information about each class, follow the MetaInfo browser links on the individual vertical pages.