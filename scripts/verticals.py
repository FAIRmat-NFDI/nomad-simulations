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
    },
    'workflow_thermodynamics': {
        'title': 'Thermodynamics Workflow',
        'purpose': 'Thermodynamics workflow for free-energy and thermodynamic property calculations',
        'sections': [
            'SerialWorkflow',
            'SerialWorkflowResults',
            'SimulationWorkflowMethod',
            'Thermodynamics',
            'ThermodynamicsMethod',
            'ThermodynamicsResults',
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
    },
    'representations': {
        'title': 'Alternative Representations',
        'purpose': 'AlternativeRepresentation subsection details: transforms and mapping to a reference representation',
        'sections': [
            'AlternativeRepresentation',
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
    },
    'chemical_formula': {
        'title': 'Chemical Formula',
        'purpose': 'Chemical formulas in different formats: descriptive, reduced, IUPAC, Hill, anonymous',
        'sections': [
            'ChemicalFormula',
        ],
    },
    # =========================================================================
    # MODEL METHOD TREE
    # =========================================================================
    'model_method': {
        'title': 'Model Method',
        'purpose': 'Base method hierarchy: BaseModelMethod, ModelMethod, and ModelMethodElectronic',
        'sections': [
            'BaseModelMethod',
            'ModelMethod',
            'ModelMethodElectronic',
        ],
    },
    'model_method_electronic': {
        'title': 'Model Method Electronic',
        'purpose': 'Electronic method subclasses branching from ModelMethodElectronic',
        'sections': [
            'ModelMethodElectronic',
            'ElectronicResponseMethod',
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
            'EOMCC',
            'CI',
            'ADC',
            'PerturbationMethod',
            'CoreHoleSpectra',
            'DMFT',
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
    },
    'spectroscopy': {
        'title': 'Spectroscopic Properties',
        'purpose': 'Spectroscopic properties: absorption, XAS, and dielectric functions',
        'sections': [
            'SpectralProfile',
            'AbsorptionSpectrum',
            'XASSpectrum',
            'Permittivity',
        ],
    },
    'thermodynamics': {
        'title': 'Thermodynamic Properties',
        'purpose': 'Thermodynamic properties: energies, forces, pressure, temperature, and state functions',
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
    },
}
