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

## [Chemical Formula](chemical_formula.md)

Chemical formulas in different formats: descriptive, reduced, IUPAC, Hill, anonymous

**In scope:** Descriptive formula, Reduced formula, IUPAC formula, Hill formula, Anonymous formula, Automatic formula generation

**Key sections:** ChemicalFormula

## [Particle States](particle_states.md)

Complete particle state hierarchy: ParticleState base class, AtomsState with detailed atomic properties, and CGBeadState

**In scope:** ParticleState: base class for all particle information, AtomsState: atomic particle states with chemical symbols, CGBeadState: coarse-grained bead states, AtomicOrbitals: quantum numbers (n, l, ml, j, mj, ms) within AtomsState, Orbital degeneracy and occupation, CoreHole: excited electron states for spectroscopy, HubbardInteractions: U matrix, U_effective, J_Hunds for correlated systems, Slater integrals for many-body interactions, Particle indices, velocities, forces, Chemical symbols and particle organization

**Key sections:** ParticleState, AtomsState, CGBeadState, AtomicOrbitals, CoreHole, HubbardInteractions

## [Symmetry](symmetry.md)

Crystallographic symmetry: local/global symmetry, space groups, point groups, Bravais lattices

**In scope:** Local and global symmetry section hierarchy, Space group symbols and numbers, Point group symbols, Bravais lattice classifications, Symmetry operations

**Key sections:** LocalSymmetry, LocalCrystalSymmetry, GlobalSymmetry, GlobalCrystalSymmetry

## [Model Method](model_method.md)

Base method hierarchy up to ModelMethodElectronic

**In scope:** Top-level inheritance chain: BaseModelMethod → ModelMethod → ModelMethodElectronic, Entry point for all electronic-method subclasses

**Key sections:** BaseModelMethod, ModelMethod, ModelMethodElectronic

## [Force Field](force_field.md)

Classical force-field model method branch rooted at ForceField

**In scope:** ForceField as a ModelMethod subclass, Potential family entry-point used by ForceField contributions, Bridge between model methods and classical interaction potentials

**Key sections:** ModelMethod, ForceField, Potential

## [Model Method Electronic](model_method_electronic.md)

Electronic method subclasses branching from ModelMethodElectronic

**In scope:** Electronic-method inheritance rooted at ModelMethodElectronic, Ground-state electronic methods (DFT, HF, CC, CI, perturbative approaches), Tight-binding family (TB, xTB, Wannier, SlaterKoster), Excited-state methodology branch (ExcitedStateMethodology, Screening, GW, BSE, TDDFT), Core-hole and many-body electronic methods (CoreHoleSpectra, DMFT)

**Key sections:** ModelMethodElectronic, DFT, TB, xTB, Wannier, SlaterKoster, ExcitedStateMethodology, Screening, GW, BSE, TDDFT, HF, CC, CI, PerturbationMethod, CoreHoleSpectra, DMFT

## [Numerical Settings](numerical_settings.md)

Computational parameters: meshes, basis sets, convergence, and discretization

**In scope:** K-point meshes and line paths for band structures, Real-space meshes and grids, Basis set specifications: plane-wave, APW, atom-centered, Convergence thresholds and maximum iterations, Smearing functions: Fermi-Dirac, Gaussian, Methfessel-Paxton, Force calculation settings

**Key sections:** NumericalSettings, Mesh, KMesh, KLinePath, KSpace, Smearing, SelfConsistency, ForceCalculations, BasisSetComponent, PlaneWaveBasisSet, APWPlaneWaveBasisSet, AtomCenteredFunction

## [Outputs](outputs.md)

Base output structure and common property definitions

**In scope:** Outputs section that references ModelSystem and ModelMethod, SCFSteps with scf_steps quantities for SCF iteration history, PhysicalProperty base class for all computed properties, Property contributions and derivations, SCF convergence data (energy deltas, density changes, etc.)

**Key sections:** Outputs, SCFSteps, PhysicalProperty

## [Electronic Structure Properties](electronic_properties.md)

Electronic eigenvalues, band structures, DOS, band gaps, occupancies, and Fermi surfaces

**In scope:** Eigenvalue hierarchy: BaseElectronicEigenvalues → ElectronicEigenvalues → ElectronicBandStructure, Band structures along high-symmetry paths, Density of states (DOS) profiles, Electronic band gaps (direct, indirect), Orbital occupancies, Fermi surface topology

**Key sections:** BaseElectronicEigenvalues, ElectronicEigenvalues, ElectronicBandStructure, ElectronicBandGap, DOSProfile, ElectronicDensityOfStates, Occupancy, FermiSurface

## [Many-Body Properties](manybody_properties.md)

Green's functions, self-energies, hybridization, quasiparticle weights, hopping matrices

**In scope:** Green's function base class and electronic specialization, Self-energies from GW and DMFT, Hybridization functions for impurity problems, Quasiparticle renormalization weights, Hopping matrices from tight-binding, Crystal field splittings in correlated systems

**Key sections:** BaseGreensFunction, ElectronicGreensFunction, ElectronicSelfEnergy, HybridizationFunction, QuasiparticleWeight, HoppingMatrix, CrystalFieldSplitting

## [Physical Property Backbone](physical_property.md)

Shared base classes for physical-property types and their common metadata structure

**In scope:** PhysicalProperty as the common base for computed properties, ErrorEstimate subsection used for uncertainty/error metadata, Abstract/base property families for electronic, Green-function, energy, force, and spectral data, Cross-domain backbone used by specialized output verticals

**Key sections:** PhysicalProperty, ErrorEstimate, BaseElectronicEigenvalues, BaseGreensFunction, BaseEnergy, BaseForce, SpectralProfile

## [Spectroscopic Properties](spectroscopy.md)

Absorption spectra, XAS, and dielectric response

**In scope:** Spectral profile base class, Absorption spectra from BSE calculations, X-ray absorption spectra (XAS) from core hole calculations, Frequency-dependent dielectric functions (permittivity)

**Key sections:** SpectralProfile, AbsorptionSpectrum, XASSpectrum, Permittivity

## [Thermodynamic Properties](thermodynamics.md)

Energies, forces, pressure, temperature, and thermodynamic state functions

**In scope:** Energy hierarchy: BaseEnergy → specific energy types, Free energies: Gibbs, Helmholtz, Force hierarchy: BaseForce → TotalForce, Thermodynamic state variables: pressure, volume, temperature, Entropy and heat capacities, Virial tensor for stress calculations, Hessian matrices for phonon calculations

**Key sections:** BaseEnergy, TotalEnergy, KineticEnergy, PotentialEnergy, Heat, Work, InternalEnergy, Enthalpy, GibbsFreeEnergy, HelmholtzFreeEnergy, ChemicalPotential, VirialTensor, BaseForce, TotalForce, Pressure, Volume, Temperature, Entropy, HeatCapacity, MassDensity, Hessian

## [Workflow Core](workflow.md)

Core workflow hierarchy and shared method/results structures

**In scope:** Workflow task abstraction and task-reference linkage, Core inheritance spine: SimulationWorkflow with serial/parallel specializations, Shared workflow model and method metadata containers, Shared workflow result timing and convergence result containers

**Key sections:** SimulationTask, SimulationTaskReference, SimulationWorkflow, SerialWorkflow, ParallelWorkflow, SimulationWorkflowModel, SimulationWorkflowMethod, WorkflowTime, SimulationWorkflowResults, SerialWorkflowResults, WorkflowConvergenceTarget, WorkflowConvergenceResults

## [Beyond-DFT Workflow Family](workflow_beyond_dft.md)

Beyond-DFT workflow base classes and derived GW/TB/DMFT/XS specializations

**In scope:** BeyondDFT inheritance backbone for workflow/method/results, Derived families: GW, DFT+TB, DFT+TB+DMFT, DMFT+MaxEnt, and XS, ElectronicStructureResults subsections used by beyond-DFT result classes

**Key sections:** SerialWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, ElectronicStructureResults, BeyondDFTWorkflow, BeyondDFTMethod, BeyondDFTResults, DFTGWWorkflow, DFTGWMethod, DFTGWResults, DFTTBWorkflow, DFTTBMethod, DFTTBResults, DFTTBDMFTWorkflow, DFTTBDMFTMethod, DFTTBDMFTResults, DMFTMaxEntWorkflow, DMTMaxEntMethod, DMTMaxEntResults, XSWorkflow, XSMethod, XSResults

## [Beyond-HF Workflow Family](workflow_beyond_hf.md)

Beyond-HF workflow base classes with CC and CI derived branches

**In scope:** BeyondHF inheritance backbone for workflow/method/results, Derived post-HF families: coupled-cluster (CC) and configuration interaction (CI), ElectronicStructureResults subsections used by beyond-HF result classes

**Key sections:** SerialWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, ElectronicStructureResults, BeyondHFWorkflow, BeyondHFMethod, BeyondHFResults, HFCCWorkflow, HFCCMethod, HFCCResults, HFCIWorkflow, HFCIMethod, HFCIResults

## [Elastic Workflow](workflow_elastic.md)

Elastic-constant workflow with thermodynamics-derived result structures

**In scope:** Elastic inheritance from SimulationWorkflow, Elastic method specialization and strain-diagram result containers, ElasticResults inheritance through ThermodynamicsResults

**Key sections:** SimulationWorkflow, SimulationWorkflowMethod, ThermodynamicsResults, Elastic, ElasticMethod, ElasticResults, StrainDiagrams

## [Equation of State Workflow](workflow_equation_of_state.md)

Parallel equation-of-state workflow with EOS fitting results

**In scope:** EquationOfState inheritance from ParallelWorkflow, EOS method specialization and EOSFit result subsections, Parallel workflow pattern for volume/energy scan calculations

**Key sections:** ParallelWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, EquationOfState, EquationOfStateMethod, EquationOfStateResults, EOSFit

## [Geometry Optimization Workflow](workflow_geometry_optimization.md)

Geometry-optimization workflow with convergence-aware method/results modeling

**In scope:** GeometryOptimization inheritance from SerialWorkflow, GeometryOptimization model and method specialization layers, Workflow and nested single-point convergence configuration/results integration

**Key sections:** SerialWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, WorkflowConvergenceTarget, GeometryOptimization, GeometryOptimizationModel, GeometryOptimizationMethod, GeometryOptimizationResults

## [Molecular Dynamics Workflow](workflow_molecular_dynamics.md)

Molecular-dynamics workflow with thermostat/barostat/shear settings and ensemble outputs

**In scope:** MolecularDynamics inheritance from SerialWorkflow, Method-side MD control settings (thermostat, barostat, shear, free-energy), Results-side ensemble/correlation properties and trajectory observables, Cross-domain anchors to NumericalSettings and PhysicalProperty for hierarchy context

**Key sections:** SerialWorkflow, SerialWorkflowResults, SimulationWorkflowMethod, NumericalSettings, PhysicalProperty, MDSettings, ThermostatParameters, BarostatParameters, ShearParameters, FreeEnergyCalculationParameters, Lambdas, EnsembleProperty, CorrelationFunction, RadialDistributionFunction, DiffusionConstant, MeanSquaredDisplacement, MolecularDynamics, MolecularDynamicsMethod, MolecularDynamicsResults

## [Phonon Workflow](workflow_phonon.md)

Phonon workflow specialization with method/results classes

**In scope:** Phonon inheritance from SimulationWorkflow, Phonon method/result specialization hierarchy, Workflow structure for finite-displacement/phonon-property computations

**Key sections:** SimulationWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, Phonon, PhononMethod, PhononResults

## [Photon Polarization Workflow](workflow_photon_polarization.md)

Parallel photon-polarization workflow and polarization-resolved results

**In scope:** PhotonPolarizationWorkflow inheritance from ParallelWorkflow, Method and result classes for polarization-dependent spectra, Parallel execution structure for multiple polarization channels

**Key sections:** ParallelWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, PhotonPolarizationWorkflow, PhotonPolarizationMethod, PhotonPolarizationResults

## [Single-Point Workflow](workflow_single_point.md)

Single-point workflow and its method/results classes

**In scope:** SinglePoint inheritance from SimulationWorkflow, SinglePoint method and results class specializations, Minimal workflow pattern for one-step calculations

**Key sections:** SimulationWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, SinglePoint, SinglePointMethod, SinglePointResults

## [Thermodynamics Workflow](workflow_thermodynamics.md)

Thermodynamics workflow specialization and serial-result integration

**In scope:** Thermodynamics inheritance from SimulationWorkflow, Thermodynamics method specialization structure, ThermodynamicsResults inheritance from SerialWorkflowResults

**Key sections:** SerialWorkflow, SerialWorkflowResults, SimulationWorkflowMethod, Thermodynamics, ThermodynamicsMethod, ThermodynamicsResults

## [Workflow Convergence](workflow_convergence.md)

Convergence target classes and workflow-level convergence result structures

**In scope:** Convergence target inheritance family and target-type specializations, Convergence result container with target references and status fields, Workflow model/results integration points for convergence configuration and outcomes, GeometryOptimization-specific convergence extensions for nested SCF contexts

**Key sections:** WorkflowConvergenceTarget, EnergyConvergenceTarget, ForceConvergenceTarget, PotentialConvergenceTarget, ChargeConvergenceTarget, WavefunctionConvergenceTarget, WorkflowConvergenceResults, SimulationWorkflowModel, SimulationWorkflowResults, GeometryOptimizationModel, GeometryOptimizationResults

## [Workflow Trajectory Properties](workflow_trajectory.md)

Serial-workflow trajectory/configurational property subsections

**In scope:** Configurational property base class for trajectory-like workflow results, Temperature, pressure, and gyration metrics over frames, Free-energy calculation trajectories linked into serial workflow results, SerialWorkflowResults containment of trajectory/configurational properties

**Key sections:** SerialWorkflowResults, ConfigurationalProperty, Temperatures, Pressures, RadiiOfGyration, FreeEnergyCalculations

