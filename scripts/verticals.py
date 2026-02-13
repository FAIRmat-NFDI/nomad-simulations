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

Vertical Organization:
Each vertical represents a "cut-out" from the schema tree, showing:
- Containment relationships (SubSection hierarchy)
- Inheritance relationships (class → parent class)
- Reference relationships (Quantity types pointing to other sections)

Verticals:
(1) simulation - Root entry point with Program
(2) model_system - Complete ModelSystem tree (representations, symmetry, particle states)
(3) representations - Representation hierarchy and cell geometry
(4) particle_states - Detailed particle and orbital properties (atoms, core holes, Hubbard)
(5) model_method - Base method hierarchy up to ModelMethodElectronic
(6) model_method_electronic - Electronic method subclasses (DFT, TB, GW, BSE, DMFT, etc.)
(7) force_field - Classical force-field method family
(8) numerical_settings - Meshes, basis sets, convergence parameters
(9) outputs - Output properties base classes
(10) physical_property - Base physical-property backbone and shared abstractions
(11) electronic_properties - Electronic structure outputs
(12) manybody_properties - Many-body theory outputs
(13) spectroscopy - Spectroscopic properties
(14) thermodynamics - Energies, forces, thermodynamic properties
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
            'HartreeFock',
            'CoupledCluster',
            'ConfigurationInteraction',
            'PerturbationMethod',
            'CoreHoleSpectra',
            'DMFT',
        ],
        'in_scope': [
            'Electronic-method inheritance rooted at ModelMethodElectronic',
            'Ground-state electronic methods (DFT, HartreeFock, coupled-cluster, CI, perturbative approaches)',
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
            'SCFOutputs',
            'PhysicalProperty',
        ],
        'in_scope': [
            'Outputs section that references ModelSystem and ModelMethod',
            'SCFOutputs with scf_steps for iteration history',
            'PhysicalProperty base class for all computed properties',
            'Property contributions and derivations',
            'SCF convergence checking',
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
