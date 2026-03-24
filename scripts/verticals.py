# scripts/verticals.py
"""
Defines documentation 'verticals' for the auto-generated MkDocs pages.

Author: JLM-FAU, JFrudzinski
Purpose: Manual curation of documentation organization following the clear schema tree structure.

Schema Structure:
- Simulation (root entry) contains 4 main subsections:
  1. Program - Software information
  2. ModelSystem - Physical system definition (recursive tree with sub_systems)
  3. ModelMethod - Computational methodology (inheritance hierarchy)
  4. Outputs - Computed properties (references back to system/method)
- Workflow classes are documented as a dedicated top-level schema branch.

Vertical Organization:
Each vertical represents a "cut-out" from the schema tree, showing:
- Containment relationships (SubSection hierarchy)
- Inheritance relationships (class → parent class)
- Reference relationships (Quantity types pointing to other sections)

Verticals:
- simulation and workflow roots
- model_system hierarchy pages
- model_method hierarchy pages
- outputs/property hierarchy pages
- workflow specialization families (single-point, geometry optimization, molecular dynamics, EOS, elastic, phonon, beyond-DFT, beyond-HF, etc.)
"""

VERTICALS = {
    # =========================================================================
    # ROOT ENTRY POINT
    # =========================================================================
    'simulation': {
        'title': 'Simulation Entry',
        'purpose': 'Root entry point for simulations: Simulation, BaseSimulation, and Program',
        'sections': [
            'Simulation',
            'BaseSimulation',
            'Program',
        ],
        'in_scope': [
            'Root Simulation section that contains all simulation metadata',
            'Timing information (cpu1_start, cpu1_end, wall_start, wall_end)',
            'Program details (name, version, link)',
            'Entry point that references the four main subsections',
        ],
    },
    # =========================================================================
    # WORKFLOW TREE
    # =========================================================================
    'workflow': {
        'title': 'Workflow Core',
        'nav_title': 'Workflow',
        'purpose': 'Core workflow hierarchy and shared method/results structures',
        'sections': [
            'SimulationTask',
            'SimulationTaskReference',
            'SimulationWorkflow',
            'SerialWorkflow',
            'ParallelWorkflow',
            'SimulationWorkflowModel',
            'SimulationWorkflowMethod',
            'WorkflowTime',
            'SimulationWorkflowResults',
            'SerialWorkflowResults',
            'WorkflowConvergenceTarget',
            'WorkflowConvergenceResults',
        ],
        'in_scope': [
            'Workflow task abstraction and task-reference linkage',
            'Core inheritance spine: SimulationWorkflow with serial/parallel specializations',
            'Shared workflow model and method metadata containers',
            'Shared workflow result timing and convergence result containers',
        ],
    },
    'workflow_convergence': {
        'title': 'Workflow Convergence',
        'purpose': 'Convergence target classes and workflow-level convergence result structures',
        'sections': [
            'WorkflowConvergenceTarget',
            'EnergyConvergenceTarget',
            'ForceConvergenceTarget',
            'PotentialConvergenceTarget',
            'ChargeConvergenceTarget',
            'WavefunctionConvergenceTarget',
            'WorkflowConvergenceResults',
            'SimulationWorkflowModel',
            'SimulationWorkflowResults',
            'GeometryOptimizationModel',
            'GeometryOptimizationResults',
        ],
        'in_scope': [
            'Convergence target inheritance family and target-type specializations',
            'Convergence result container with target references and status fields',
            'Workflow model/results integration points for convergence configuration and outcomes',
            'GeometryOptimization-specific convergence extensions for nested SCF contexts',
        ],
    },
    'workflow_trajectory': {
        'title': 'Workflow Trajectory Properties',
        'purpose': 'Serial-workflow trajectory/configurational property subsections',
        'sections': [
            'SerialWorkflowResults',
            'ConfigurationalProperty',
            'Temperatures',
            'Pressures',
            'RadiiOfGyration',
            'FreeEnergyCalculations',
        ],
        'in_scope': [
            'Configurational property base class for trajectory-like workflow results',
            'Temperature, pressure, and gyration metrics over frames',
            'Free-energy calculation trajectories linked into serial workflow results',
            'SerialWorkflowResults containment of trajectory/configurational properties',
        ],
    },
    'workflow_single_point': {
        'title': 'Single-Point Workflow',
        'purpose': 'Single-point workflow and its method/results classes',
        'sections': [
            'SimulationWorkflow',
            'SimulationWorkflowMethod',
            'SimulationWorkflowResults',
            'SinglePoint',
            'SinglePointMethod',
            'SinglePointResults',
        ],
        'in_scope': [
            'SinglePoint inheritance from SimulationWorkflow',
            'SinglePoint method and results class specializations',
            'Minimal workflow pattern for one-step calculations',
        ],
    },
    'workflow_geometry_optimization': {
        'title': 'Geometry Optimization Workflow',
        'purpose': 'Geometry-optimization workflow with convergence-aware method/results modeling',
        'sections': [
            'SerialWorkflow',
            'SimulationWorkflowMethod',
            'SimulationWorkflowResults',
            'WorkflowConvergenceTarget',
            'GeometryOptimization',
            'GeometryOptimizationModel',
            'GeometryOptimizationMethod',
            'GeometryOptimizationResults',
        ],
        'in_scope': [
            'GeometryOptimization inheritance from SerialWorkflow',
            'GeometryOptimization model and method specialization layers',
            'Workflow and nested single-point convergence configuration/results integration',
        ],
    },
    'workflow_molecular_dynamics': {
        'title': 'Molecular Dynamics Workflow',
        'purpose': 'Molecular-dynamics workflow with thermostat/barostat/shear settings and ensemble outputs',
        'sections': [
            'SerialWorkflow',
            'SerialWorkflowResults',
            'SimulationWorkflowMethod',
            'NumericalSettings',
            'PhysicalProperty',
            'MDSettings',
            'ThermostatParameters',
            'BarostatParameters',
            'ShearParameters',
            'FreeEnergyCalculationParameters',
            'Lambdas',
            'EnsembleProperty',
            'CorrelationFunction',
            'RadialDistributionFunction',
            'DiffusionConstant',
            'MeanSquaredDisplacement',
            'MolecularDynamics',
            'MolecularDynamicsMethod',
            'MolecularDynamicsResults',
        ],
        'in_scope': [
            'MolecularDynamics inheritance from SerialWorkflow',
            'Method-side MD control settings (thermostat, barostat, shear, free-energy)',
            'Results-side ensemble/correlation properties and trajectory observables',
            'Cross-domain anchors to NumericalSettings and PhysicalProperty for hierarchy context',
        ],
    },
    'workflow_thermodynamics': {
        'title': 'Thermodynamics Workflow',
        'purpose': 'Thermodynamics workflow specialization and serial-result integration',
        'sections': [
            'SerialWorkflow',
            'SerialWorkflowResults',
            'SimulationWorkflowMethod',
            'Thermodynamics',
            'ThermodynamicsMethod',
            'ThermodynamicsResults',
        ],
        'in_scope': [
            'Thermodynamics inheritance from SimulationWorkflow',
            'Thermodynamics method specialization structure',
            'ThermodynamicsResults inheritance from SerialWorkflowResults',
        ],
    },
    'workflow_equation_of_state': {
        'title': 'Equation of State Workflow',
        'purpose': 'Parallel equation-of-state workflow with EOS fitting results',
        'sections': [
            'ParallelWorkflow',
            'SimulationWorkflowMethod',
            'SimulationWorkflowResults',
            'EquationOfState',
            'EquationOfStateMethod',
            'EquationOfStateResults',
            'EOSFit',
        ],
        'in_scope': [
            'EquationOfState inheritance from ParallelWorkflow',
            'EOS method specialization and EOSFit result subsections',
            'Parallel workflow pattern for volume/energy scan calculations',
        ],
    },
    'workflow_elastic': {
        'title': 'Elastic Workflow',
        'purpose': 'Elastic-constant workflow with thermodynamics-derived result structures',
        'sections': [
            'SimulationWorkflow',
            'SimulationWorkflowMethod',
            'ThermodynamicsResults',
            'Elastic',
            'ElasticMethod',
            'ElasticResults',
            'StrainDiagrams',
        ],
        'in_scope': [
            'Elastic inheritance from SimulationWorkflow',
            'Elastic method specialization and strain-diagram result containers',
            'ElasticResults inheritance through ThermodynamicsResults',
        ],
    },
    'workflow_phonon': {
        'title': 'Phonon Workflow',
        'purpose': 'Phonon workflow specialization with method/results classes',
        'sections': [
            'SimulationWorkflow',
            'SimulationWorkflowMethod',
            'SimulationWorkflowResults',
            'Phonon',
            'PhononMethod',
            'PhononResults',
        ],
        'in_scope': [
            'Phonon inheritance from SimulationWorkflow',
            'Phonon method/result specialization hierarchy',
            'Workflow structure for finite-displacement/phonon-property computations',
        ],
    },
    'workflow_photon_polarization': {
        'title': 'Photon Polarization Workflow',
        'purpose': 'Parallel photon-polarization workflow and polarization-resolved results',
        'sections': [
            'ParallelWorkflow',
            'SimulationWorkflowMethod',
            'SimulationWorkflowResults',
            'PhotonPolarizationWorkflow',
            'PhotonPolarizationMethod',
            'PhotonPolarizationResults',
        ],
        'in_scope': [
            'PhotonPolarizationWorkflow inheritance from ParallelWorkflow',
            'Method and result classes for polarization-dependent spectra',
            'Parallel execution structure for multiple polarization channels',
        ],
    },
    'workflow_beyond_dft': {
        'title': 'Beyond-DFT Workflow Family',
        'purpose': 'Beyond-DFT workflow base classes and derived GW/TB/DMFT/XS specializations',
        'sections': [
            'SerialWorkflow',
            'SimulationWorkflowMethod',
            'SimulationWorkflowResults',
            'ElectronicStructureResults',
            'BeyondDFTWorkflow',
            'BeyondDFTMethod',
            'BeyondDFTResults',
            'DFTGWWorkflow',
            'DFTGWMethod',
            'DFTGWResults',
            'DFTTBWorkflow',
            'DFTTBMethod',
            'DFTTBResults',
            'DFTTBDMFTWorkflow',
            'DFTTBDMFTMethod',
            'DFTTBDMFTResults',
            'DMFTMaxEntWorkflow',
            'DMTMaxEntMethod',
            'DMTMaxEntResults',
            'XSWorkflow',
            'XSMethod',
            'XSResults',
        ],
        'in_scope': [
            'BeyondDFT inheritance backbone for workflow/method/results',
            'Derived families: GW, DFT+TB, DFT+TB+DMFT, DMFT+MaxEnt, and XS',
            'ElectronicStructureResults subsections used by beyond-DFT result classes',
        ],
    },
    'workflow_beyond_hf': {
        'title': 'Beyond-HF Workflow Family',
        'purpose': 'Beyond-HF workflow base classes with CC and CI derived branches',
        'sections': [
            'SerialWorkflow',
            'SimulationWorkflowMethod',
            'SimulationWorkflowResults',
            'ElectronicStructureResults',
            'BeyondHFWorkflow',
            'BeyondHFMethod',
            'BeyondHFResults',
            'HFCCWorkflow',
            'HFCCMethod',
            'HFCCResults',
            'HFCIWorkflow',
            'HFCIMethod',
            'HFCIResults',
        ],
        'in_scope': [
            'BeyondHF inheritance backbone for workflow/method/results',
            'Derived post-HF families: coupled-cluster (CC) and configuration interaction (CI)',
            'ElectronicStructureResults subsections used by beyond-HF result classes',
        ],
    },
    # =========================================================================
    # MODEL SYSTEM TREE
    # =========================================================================
    'model_system': {
        'title': 'Model System',
        'purpose': 'Root ModelSystem section with direct representation relationships and complete system tree',
        'sections': [
            'ModelSystem',
            'Representation',
            'AlternativeRepresentation',
        ],
        'in_scope': [
            'ModelSystem as the root of the system tree',
            'Recursive sub_systems containment (ModelSystem contains ModelSystem)',
            'System type and dimensionality',
            'Direct relationships to Representation and AlternativeRepresentation',
            'References to ParticleState, Local/Global symmetry, and ChemicalFormula subsections',
        ],
    },
    'representations': {
        'title': 'Alternative Representations',
        'purpose': 'AlternativeRepresentation subsection details: transforms and mapping to a reference representation',
        'sections': [
            'AlternativeRepresentation',
        ],
        'in_scope': [
            'AlternativeRepresentation subsection of ModelSystem',
            'Reference representation linkage',
            'Transformation matrix and origin shift between representations',
            'How alternative cells are mapped from the original representation',
        ],
    },
    'particle_states': {
        'title': 'Particle States',
        'purpose': 'Complete particle state hierarchy: ParticleState base class, AtomsState with detailed atomic properties, and CGBeadState',
        'sections': [
            'ParticleState',
            'AtomsState',
            'CGBeadState',
            'AtomicOrbitals',
            'CoreHole',
            'HubbardInteractions',
        ],
        'in_scope': [
            'ParticleState: base class for all particle information',
            'AtomsState: atomic particle states with chemical symbols',
            'CGBeadState: coarse-grained bead states',
            'AtomicOrbitals: quantum numbers (n, l, ml, j, mj, ms) within AtomsState',
            'Orbital degeneracy and occupation',
            'CoreHole: excited electron states for spectroscopy',
            'HubbardInteractions: U matrix, U_effective, J_Hunds for correlated systems',
            'Slater integrals for many-body interactions',
            'Particle indices, velocities, forces',
            'Chemical symbols and particle organization',
        ],
    },
    'symmetry': {
        'title': 'Symmetry',
        'purpose': 'Crystallographic symmetry: local/global symmetry, space groups, point groups, Bravais lattices',
        'sections': [
            'LocalSymmetry',
            'LocalCrystalSymmetry',
            'GlobalSymmetry',
            'GlobalCrystalSymmetry',
        ],
        'in_scope': [
            'Local and global symmetry section hierarchy',
            'Space group symbols and numbers',
            'Point group symbols',
            'Bravais lattice classifications',
            'Symmetry operations',
        ],
    },
    'chemical_formula': {
        'title': 'Chemical Formula',
        'purpose': 'Chemical formulas in different formats: descriptive, reduced, IUPAC, Hill, anonymous',
        'sections': [
            'ChemicalFormula',
        ],
        'in_scope': [
            'Descriptive formula',
            'Reduced formula',
            'IUPAC formula',
            'Hill formula',
            'Anonymous formula',
            'Automatic formula generation',
        ],
    },
    # =========================================================================
    # MODEL METHOD TREE
    # =========================================================================
    'model_method': {
        'title': 'Model Method',
        'purpose': 'Base method hierarchy up to ModelMethodElectronic',
        'sections': [
            'BaseModelMethod',
            'ModelMethod',
            'ModelMethodElectronic',
        ],
        'in_scope': [
            'Top-level inheritance chain: BaseModelMethod → ModelMethod → ModelMethodElectronic',
            'Entry point for all electronic-method subclasses',
        ],
    },
    'model_method_electronic': {
        'title': 'Model Method Electronic',
        'purpose': 'Electronic method subclasses branching from ModelMethodElectronic',
        'sections': [
            'ModelMethodElectronic',
            'DFT',
            'TB',
            'xTB',
            'Wannier',
            'SlaterKoster',
            'ExcitedStateMethodology',
            'Screening',
            'GW',
            'BSE',
            'TDDFT',
            'HF',
            'CC',
            'CI',
            'PerturbationMethod',
            'CoreHoleSpectra',
            'DMFT',
        ],
        'in_scope': [
            'Electronic-method inheritance rooted at ModelMethodElectronic',
            'Ground-state electronic methods (DFT, HF, CC, CI, perturbative approaches)',
            'Tight-binding family (TB, xTB, Wannier, SlaterKoster)',
            'Excited-state methodology branch (ExcitedStateMethodology, Screening, GW, BSE, TDDFT)',
            'Core-hole and many-body electronic methods (CoreHoleSpectra, DMFT)',
        ],
    },
    'force_field': {
        'title': 'Force Field',
        'purpose': 'Classical force-field model method branch rooted at ForceField',
        'sections': [
            'ModelMethod',
            'ForceField',
            'Potential',
        ],
        'in_scope': [
            'ForceField as a ModelMethod subclass',
            'Potential family entry-point used by ForceField contributions',
            'Bridge between model methods and classical interaction potentials',
        ],
    },
    'numerical_settings': {
        'title': 'Numerical Settings',
        'purpose': 'Computational parameters: meshes, basis sets, convergence, and discretization',
        'sections': [
            'NumericalSettings',
            'Mesh',
            'KMesh',
            'KLinePath',
            'KSpace',
            'Smearing',
            'SelfConsistency',
            'ForceCalculations',
            'BasisSetComponent',
            'PlaneWaveBasisSet',
            'APWPlaneWaveBasisSet',
            'AtomCenteredFunction',
        ],
        'in_scope': [
            'K-point meshes and line paths for band structures',
            'Real-space meshes and grids',
            'Basis set specifications: plane-wave, APW, atom-centered',
            'Convergence thresholds and maximum iterations',
            'Smearing functions: Fermi-Dirac, Gaussian, Methfessel-Paxton',
            'Force calculation settings',
        ],
    },
    # =========================================================================
    # OUTPUTS TREE
    # =========================================================================
    'outputs': {
        'title': 'Outputs',
        'purpose': 'Base output structure and common property definitions',
        'sections': [
            'Outputs',
            'SCFSteps',
            'PhysicalProperty',
        ],
        'in_scope': [
            'Outputs section that references ModelSystem and ModelMethod',
            'SCFSteps with scf_steps quantities for SCF iteration history',
            'PhysicalProperty base class for all computed properties',
            'Property contributions and derivations',
            'SCF convergence data (energy deltas, density changes, etc.)',
        ],
    },
    'physical_property': {
        'title': 'Physical Property Backbone',
        'purpose': 'Shared base classes for physical-property types and their common metadata structure',
        'sections': [
            'PhysicalProperty',
            'ErrorEstimate',
            'BaseElectronicEigenvalues',
            'BaseGreensFunction',
            'BaseEnergy',
            'BaseForce',
            'SpectralProfile',
        ],
        'in_scope': [
            'PhysicalProperty as the common base for computed properties',
            'ErrorEstimate subsection used for uncertainty/error metadata',
            'Abstract/base property families for electronic, Green-function, energy, force, and spectral data',
            'Cross-domain backbone used by specialized output verticals',
        ],
    },
    'electronic_properties': {
        'title': 'Electronic Structure Properties',
        'purpose': 'Electronic eigenvalues, band structures, DOS, band gaps, occupancies, and Fermi surfaces',
        'sections': [
            'BaseElectronicEigenvalues',
            'ElectronicEigenvalues',
            'ElectronicBandStructure',
            'ElectronicBandGap',
            'DOSProfile',
            'ElectronicDensityOfStates',
            'Occupancy',
            'FermiSurface',
        ],
        'in_scope': [
            'Eigenvalue hierarchy: BaseElectronicEigenvalues → ElectronicEigenvalues → ElectronicBandStructure',
            'Band structures along high-symmetry paths',
            'Density of states (DOS) profiles',
            'Electronic band gaps (direct, indirect)',
            'Orbital occupancies',
            'Fermi surface topology',
        ],
    },
    'manybody_properties': {
        'title': 'Many-Body Properties',
        'purpose': "Green's functions, self-energies, hybridization, quasiparticle weights, hopping matrices",
        'sections': [
            'BaseGreensFunction',
            'ElectronicGreensFunction',
            'ElectronicSelfEnergy',
            'HybridizationFunction',
            'QuasiparticleWeight',
            'HoppingMatrix',
            'CrystalFieldSplitting',
        ],
        'in_scope': [
            "Green's function base class and electronic specialization",
            'Self-energies from GW and DMFT',
            'Hybridization functions for impurity problems',
            'Quasiparticle renormalization weights',
            'Hopping matrices from tight-binding',
            'Crystal field splittings in correlated systems',
        ],
    },
    'spectroscopy': {
        'title': 'Spectroscopic Properties',
        'purpose': 'Absorption spectra, XAS, and dielectric response',
        'sections': [
            'SpectralProfile',
            'AbsorptionSpectrum',
            'XASSpectrum',
            'Permittivity',
        ],
        'in_scope': [
            'Spectral profile base class',
            'Absorption spectra from BSE calculations',
            'X-ray absorption spectra (XAS) from core hole calculations',
            'Frequency-dependent dielectric functions (permittivity)',
        ],
    },
    'thermodynamics': {
        'title': 'Thermodynamic Properties',
        'purpose': 'Energies, forces, pressure, temperature, and thermodynamic state functions',
        'sections': [
            'BaseEnergy',
            'TotalEnergy',
            'KineticEnergy',
            'PotentialEnergy',
            'Heat',
            'Work',
            'InternalEnergy',
            'Enthalpy',
            'GibbsFreeEnergy',
            'HelmholtzFreeEnergy',
            'ChemicalPotential',
            'VirialTensor',
            'BaseForce',
            'TotalForce',
            'Pressure',
            'Volume',
            'Temperature',
            'Entropy',
            'HeatCapacity',
            'MassDensity',
            'Hessian',
        ],
        'in_scope': [
            'Energy hierarchy: BaseEnergy → specific energy types',
            'Free energies: Gibbs, Helmholtz',
            'Force hierarchy: BaseForce → TotalForce',
            'Thermodynamic state variables: pressure, volume, temperature',
            'Entropy and heat capacities',
            'Virial tensor for stress calculations',
            'Hessian matrices for phonon calculations',
        ],
    },
}
