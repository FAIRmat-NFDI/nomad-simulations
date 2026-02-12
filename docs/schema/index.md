# Schema Documentation

This section contains auto-generated documentation for the NOMAD simulations schema.

The schema is organized into vertical domains, each covering a specific aspect of simulation metadata:

## [Simulation Entry](simulation.md)

Root entry point for simulations: Simulation, BaseSimulation, and Program

**In scope:** Root Simulation section that contains all simulation metadata, Timing information (cpu1_start, cpu1_end, wall_start, wall_end), Program details (name, version, link), Entry point that references the four main subsections

**Key sections:** Simulation, BaseSimulation, Program

## [Model System](model_system.md)

Root ModelSystem section with direct representation relationships and complete system tree

**In scope:** ModelSystem as the root of the system tree, Recursive sub_systems containment (ModelSystem contains ModelSystem), System type and dimensionality, Direct relationships to Representation and AlternativeRepresentation, References to ParticleState, Local/Global symmetry, and ChemicalFormula subsections

**Key sections:** ModelSystem, Representation, AlternativeRepresentation

## [Alternative Representations](representations.md)

AlternativeRepresentation subsection details: transforms and mapping to a reference representation

**In scope:** AlternativeRepresentation subsection of ModelSystem, Reference representation linkage, Transformation matrix and origin shift between representations, How alternative cells are mapped from the original representation

**Key sections:** AlternativeRepresentation

## [Particle States](particle_states.md)

Complete particle state hierarchy: ParticleState base class, AtomsState with detailed atomic properties, and CGBeadState

**In scope:** ParticleState: base class for all particle information, AtomsState: atomic particle states with chemical symbols, CGBeadState: coarse-grained bead states, AtomicOrbitals: quantum numbers (n, l, ml, j, mj, ms) within AtomsState, Orbital degeneracy and occupation, CoreHole: excited electron states for spectroscopy, HubbardInteractions: U matrix, U_effective, J_Hunds for correlated systems, Slater integrals for many-body interactions, Particle indices, velocities, forces, Chemical symbols and particle organization

**Key sections:** ParticleState, AtomsState, CGBeadState, AtomicOrbitals, CoreHole, HubbardInteractions

## [Symmetry](symmetry.md)

Crystallographic symmetry: local/global symmetry, space groups, point groups, Bravais lattices

**In scope:** Local and global symmetry section hierarchy, Space group symbols and numbers, Point group symbols, Bravais lattice classifications, Symmetry operations

**Key sections:** LocalSymmetry, LocalCrystalSymmetry, GlobalSymmetry, GlobalCrystalSymmetry

## [Chemical Formula](chemical_formula.md)

Chemical formulas in different formats: descriptive, reduced, IUPAC, Hill, anonymous

**In scope:** Descriptive formula, Reduced formula, IUPAC formula, Hill formula, Anonymous formula, Automatic formula generation

**Key sections:** ChemicalFormula

## [Model Method](model_method.md)

Base method hierarchy up to ModelMethodElectronic

**In scope:** Top-level inheritance chain: BaseModelMethod → ModelMethod → ModelMethodElectronic, Entry point for all electronic-method subclasses

**Key sections:** BaseModelMethod, ModelMethod, ModelMethodElectronic

## [Model Method Electronic](model_method_electronic.md)

Electronic method subclasses branching from ModelMethodElectronic

**In scope:** Electronic-method inheritance rooted at ModelMethodElectronic, Ground-state electronic methods (DFT, HartreeFock, coupled-cluster, CI, perturbative approaches), Tight-binding family (TB, xTB, Wannier, SlaterKoster), Excited-state methodology branch (ExcitedStateMethodology, Screening, GW, BSE, TDDFT), Core-hole and many-body electronic methods (CoreHoleSpectra, DMFT)

**Key sections:** ModelMethodElectronic, DFT, TB, xTB, Wannier, SlaterKoster, ExcitedStateMethodology, Screening, GW, BSE, TDDFT, HartreeFock, CoupledCluster, ConfigurationInteraction, PerturbationMethod, CoreHoleSpectra, DMFT

## [Force Field](force_field.md)

Classical force-field model method branch rooted at ForceField

**In scope:** ForceField as a ModelMethod subclass, Potential family entry-point used by ForceField contributions, Bridge between model methods and classical interaction potentials

**Key sections:** ModelMethod, ForceField, Potential

## [Numerical Settings](numerical_settings.md)

Computational parameters: meshes, basis sets, convergence, and discretization

**In scope:** K-point meshes and line paths for band structures, Real-space meshes and grids, Basis set specifications: plane-wave, APW, atom-centered, Convergence thresholds and maximum iterations, Smearing functions: Fermi-Dirac, Gaussian, Methfessel-Paxton, Force calculation settings

**Key sections:** NumericalSettings, Mesh, KMesh, KLinePath, KSpace, Smearing, SelfConsistency, ForceCalculations, BasisSetComponent, PlaneWaveBasisSet, APWPlaneWaveBasisSet, AtomCenteredFunction

## [Outputs](outputs.md)

Base output structure and common property definitions

**In scope:** Outputs section that references ModelSystem and ModelMethod, SCFOutputs with scf_steps for iteration history, PhysicalProperty base class for all computed properties, Property contributions and derivations, SCF convergence checking

**Key sections:** Outputs, SCFOutputs, PhysicalProperty

## [Physical Property Backbone](physical_property.md)

Shared base classes for physical-property types and their common metadata structure

**In scope:** PhysicalProperty as the common base for computed properties, ErrorEstimate subsection used for uncertainty/error metadata, Abstract/base property families for electronic, Green-function, energy, force, and spectral data, Cross-domain backbone used by specialized output verticals

**Key sections:** PhysicalProperty, ErrorEstimate, BaseElectronicEigenvalues, BaseGreensFunction, BaseEnergy, BaseForce, SpectralProfile

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