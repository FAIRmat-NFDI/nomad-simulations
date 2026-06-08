# Schema Documentation

This section contains auto-generated documentation for the NOMAD simulations schema.

The schema is organized into vertical domains, each covering a specific aspect of simulation metadata:

## [Simulation Entry](simulation.md)

Root entry point for simulations: Simulation, BaseSimulation, and Program

**Key sections:** Simulation, BaseSimulation, Program

## [Model System](model_system.md)

Root ModelSystem section with direct representation relationships and complete system tree

**Key sections:** ModelSystem, Representation, AlternativeRepresentation

## [Alternative Representations](representations.md)

AlternativeRepresentation subsection details: transforms and mapping to a reference representation

**Key sections:** AlternativeRepresentation

## [Chemical Formula](chemical_formula.md)

Chemical formulas in different formats: descriptive, reduced, IUPAC, Hill, anonymous

**Key sections:** ChemicalFormula

## [Particle States](particle_states.md)

Complete particle state hierarchy: ParticleState base class, AtomsState with detailed atomic properties, and CGBeadState

**Key sections:** ParticleState, AtomsState, CGBeadState, AtomicOrbitals, CoreHole, HubbardInteractions

## [Symmetry](symmetry.md)

Crystallographic symmetry: local/global symmetry, space groups, point groups, Bravais lattices

**Key sections:** LocalSymmetry, LocalCrystalSymmetry, GlobalSymmetry, GlobalCrystalSymmetry

## [Model Method](model_method.md)

Base method hierarchy: BaseModelMethod, ModelMethod, and ModelMethodElectronic

**Key sections:** BaseModelMethod, ModelMethod, ModelMethodElectronic

## [Force Field](force_field.md)

Classical force-field model method branch rooted at ForceField

**Key sections:** ModelMethod, ForceField, Potential

## [Model Method Electronic](model_method_electronic.md)

Electronic method subclasses branching from ModelMethodElectronic

**Key sections:** ModelMethodElectronic, DFT, TB, xTB, Wannier, SlaterKoster, NDDO, ExcitedStateMethodology, Screening, GW, BSE, TDDFT, HF, CC, CI, PerturbationMethod, CoreHoleSpectra, DMFT

## [Numerical Settings](numerical_settings.md)

Computational parameters: meshes, basis sets, convergence, and discretization

**Key sections:** NumericalSettings, Mesh, KMesh, KLinePath, KSpace, Smearing, SelfConsistency, ForceCalculations, BasisSetComponent, PlaneWaveBasisSet, APWPlaneWaveBasisSet, AtomCenteredFunction

## [Outputs](outputs.md)

Base output structure and common property definitions

**Key sections:** Outputs, SCFSteps, PhysicalProperty

## [Electronic Structure Properties](electronic_properties.md)

Electronic eigenvalues, band structures, DOS, band gaps, occupancies, and Fermi surfaces

**Key sections:** BaseElectronicEigenvalues, ElectronicEigenvalues, ElectronicBandStructure, ElectronicBandGap, DOSProfile, ElectronicDensityOfStates, Occupancy, FermiSurface

## [Many-Body Properties](manybody_properties.md)

Green's functions, self-energies, hybridization, quasiparticle weights, hopping matrices

**Key sections:** BaseGreensFunction, ElectronicGreensFunction, ElectronicSelfEnergy, HybridizationFunction, QuasiparticleWeight, HoppingMatrix, CrystalFieldSplitting

## [Physical Property Backbone](physical_property.md)

Shared base classes for physical-property types and their common metadata structure

**Key sections:** PhysicalProperty, ErrorEstimate, BaseElectronicEigenvalues, BaseGreensFunction, BaseEnergy, BaseForce, SpectralProfile

## [Spectroscopic Properties](spectroscopy.md)

Spectroscopic properties: absorption, XAS, and dielectric functions

**Key sections:** SpectralProfile, AbsorptionSpectrum, XASSpectrum, Permittivity

## [Thermodynamic Properties](thermodynamics.md)

Thermodynamic properties: energies, forces, pressure, temperature, and state functions

**Key sections:** BaseEnergy, TotalEnergy, KineticEnergy, PotentialEnergy, Heat, Work, InternalEnergy, Enthalpy, GibbsFreeEnergy, HelmholtzFreeEnergy, ChemicalPotential, VirialTensor, BaseForce, TotalForce, Pressure, Volume, Temperature, Entropy, HeatCapacity, MassDensity, Hessian

## [Workflow Core](workflow.md)

Core workflow hierarchy and shared method/results structures

**Key sections:** SimulationTask, SimulationTaskReference, SimulationWorkflow, SerialWorkflow, ParallelWorkflow, SimulationWorkflowModel, SimulationWorkflowMethod, WorkflowTime, SimulationWorkflowResults, SerialWorkflowResults, WorkflowConvergenceTarget, WorkflowConvergenceResults

## [Beyond-DFT Workflow Family](workflow_beyond_dft.md)

Beyond-DFT workflow base classes and derived GW/TB/DMFT/XS specializations

**Key sections:** SerialWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, ElectronicStructureResults, BeyondDFTWorkflow, BeyondDFTMethod, BeyondDFTResults, LocalCCWorkflow, LocalCCWorkflowMethod, LocalCCWorkflowResults, DFTLocalCCWorkflow, DFTLocalCCMethod, DFTLocalCCResults, DFTGWWorkflow, DFTGWMethod, DFTGWResults, DFTTBWorkflow, DFTTBMethod, DFTTBResults, DFTTBDMFTWorkflow, DFTTBDMFTMethod, DFTTBDMFTResults, DMFTMaxEntWorkflow, DMTMaxEntMethod, DMTMaxEntResults, XSWorkflow, XSMethod, XSResults

## [Beyond-HF Workflow Family](workflow_beyond_hf.md)

Beyond-HF workflow base classes with CC and CI derived branches

**Key sections:** SerialWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, ElectronicStructureResults, BeyondHFWorkflow, BeyondHFMethod, BeyondHFResults, HFCCWorkflow, HFCCMethod, HFCCResults, HFLocalCCWorkflow, HFLocalCCMethod, HFLocalCCResults, HFCIWorkflow, HFCIMethod, HFCIResults

## [Elastic Workflow](workflow_elastic.md)

Elastic-constant workflow with thermodynamics-derived result structures

**Key sections:** SimulationWorkflow, SimulationWorkflowMethod, ThermodynamicsResults, Elastic, ElasticMethod, ElasticResults, StrainDiagrams

## [Equation of State Workflow](workflow_equation_of_state.md)

Parallel equation-of-state workflow with EOS fitting results

**Key sections:** ParallelWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, EquationOfState, EquationOfStateMethod, EquationOfStateResults, EOSFit

## [Geometry Optimization Workflow](workflow_geometry_optimization.md)

Geometry-optimization workflow with convergence-aware method/results modeling

**Key sections:** SerialWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, WorkflowConvergenceTarget, GeometryOptimization, GeometryOptimizationModel, GeometryOptimizationMethod, GeometryOptimizationResults

## [Molecular Dynamics Workflow](workflow_molecular_dynamics.md)

Molecular-dynamics workflow with thermostat/barostat/shear settings and ensemble outputs

**Key sections:** SerialWorkflow, SerialWorkflowResults, SimulationWorkflowMethod, NumericalSettings, PhysicalProperty, MDSettings, ThermostatParameters, BarostatParameters, ShearParameters, FreeEnergyCalculationParameters, Lambdas, EnsembleProperty, CorrelationFunction, RadialDistributionFunction, DiffusionConstant, MeanSquaredDisplacement, MolecularDynamics, MolecularDynamicsMethod, MolecularDynamicsResults

## [Phonon Workflow](workflow_phonon.md)

Phonon workflow specialization with method/results classes

**Key sections:** SimulationWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, Phonon, PhononMethod, PhononResults

## [Photon Polarization Workflow](workflow_photon_polarization.md)

Parallel photon-polarization workflow and polarization-resolved results

**Key sections:** ParallelWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, PhotonPolarizationWorkflow, PhotonPolarizationMethod, PhotonPolarizationResults

## [Single-Point Workflow](workflow_single_point.md)

Single-point workflow and its method/results classes

**Key sections:** SimulationWorkflow, SimulationWorkflowMethod, SimulationWorkflowResults, SinglePoint, SinglePointMethod, SinglePointResults

## [Thermodynamics Workflow](workflow_thermodynamics.md)

Thermodynamics workflow for free-energy and thermodynamic property calculations

**Key sections:** SerialWorkflow, SerialWorkflowResults, SimulationWorkflowMethod, Thermodynamics, ThermodynamicsMethod, ThermodynamicsResults

## [Workflow Convergence](workflow_convergence.md)

Convergence target classes and workflow-level convergence result structures

**Key sections:** WorkflowConvergenceTarget, EnergyConvergenceTarget, ForceConvergenceTarget, PotentialConvergenceTarget, ChargeConvergenceTarget, WavefunctionConvergenceTarget, WorkflowConvergenceResults, SimulationWorkflowModel, SimulationWorkflowResults, GeometryOptimizationModel, GeometryOptimizationResults

## [Workflow Trajectory Properties](workflow_trajectory.md)

Serial-workflow trajectory/configurational property subsections

**Key sections:** SerialWorkflowResults, ConfigurationalProperty, Temperatures, Pressures, RadiiOfGyration, FreeEnergyCalculations

