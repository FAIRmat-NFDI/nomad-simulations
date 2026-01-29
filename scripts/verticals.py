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
(2) model_system - Complete ModelSystem tree (cells, symmetry, particle states)
(3) atoms_state - Detailed atomic properties (orbitals, core holes, Hubbard)
(4) model_method - Method hierarchy (DFT, TB, GW, BSE, DMFT)
(5) numerical_settings - Meshes, basis sets, convergence parameters
(6) outputs - Output properties base classes
(7) electronic_properties - Electronic structure outputs
(8) manybody_properties - Many-body theory outputs
(9) spectroscopy - Spectroscopic properties
(10) thermodynamics - Energies, forces, thermodynamic properties
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
        'out_of_scope': [
            'ModelSystem details (see model_system vertical)',
            'ModelMethod details (see model_method vertical)',
            'Outputs details (see dedicated output verticals)',
            'Workflow classes (separate schema)',
        ],
    },
    # =========================================================================
    # MODEL SYSTEM TREE
    # =========================================================================
    'model_system': {
        'title': 'Model System',
        'purpose': 'Complete ModelSystem tree: geometric spaces, cells, symmetry, and particle organization',
        'sections': [
            'ModelSystem',
            'GeometricSpace',
            'Cell',
            'AtomicCell',
            'Symmetry',
            'ChemicalFormula',
            'ParticleState',
            'AtomsState',
            'CGBeadState',
        ],
        'in_scope': [
            'ModelSystem as the root of the system tree',
            'Geometric spaces: Cell and AtomicCell with lattice vectors',
            'Symmetry information: space groups, point groups, Bravais lattices',
            'Chemical formulas: descriptive, reduced, IUPAC, Hill, anonymous',
            'Particle states: AtomsState for atoms, CGBeadState for coarse-grained beads',
            'Recursive sub_systems containment (ModelSystem contains ModelSystem)',
            'Positions, velocities, particle_indices',
            'System type and dimensionality',
        ],
        'out_of_scope': [
            'Detailed atomic properties like orbitals (see atoms_state)',
            'Core holes and Hubbard interactions (see atoms_state)',
            'Methods that use the system (see model_method)',
            'Outputs computed from the system (see output verticals)',
        ],
    },
    'atoms_state': {
        'title': 'Atomic State Properties',
        'purpose': 'Detailed atomic-level properties within AtomsState: orbitals, core holes, and Hubbard interactions',
        'sections': [
            'AtomsState',
            'OrbitalsState',
            'CoreHole',
            'HubbardInteractions',
        ],
        'in_scope': [
            'AtomsState as the container for atomic property details',
            'OrbitalsState: quantum numbers (n, l, ml, j, mj, ms)',
            'Orbital degeneracy and occupation',
            'CoreHole: excited electron states for spectroscopy',
            'HubbardInteractions: U matrix, U_effective, J_Hunds for correlated systems',
            'Slater integrals for many-body interactions',
        ],
        'out_of_scope': [
            'Basic particle positions and velocities (see model_system)',
            'Cell and geometric information (see model_system)',
            'Methods that use these properties like DMFT (see model_method)',
            'CoreHoleSpectra method (see model_method)',
        ],
    },
    # =========================================================================
    # MODEL METHOD TREE
    # =========================================================================
    'model_method': {
        'title': 'Model Methods',
        'purpose': 'Complete ModelMethod tree: electronic structure methods and their hierarchy',
        'sections': [
            'BaseModelMethod',
            'ModelMethod',
            'ModelMethodElectronic',
            'DFT',
            'XCFunctional',
            'TB',
            'Wannier',
            'SlaterKoster',
            'SlaterKosterBond',
            'xTB',
            'ExcitedStateMethodology',
            'Screening',
            'GW',
            'BSE',
            'CoreHoleSpectra',
            'Photon',
            'DMFT',
        ],
        'in_scope': [
            'Method inheritance hierarchy: BaseModelMethod → ModelMethod → ModelMethodElectronic',
            'DFT: Jacobs ladder, XC functionals, exact exchange, van der Waals',
            'Tight-binding (TB): DFTB, xTB, Wannier, Slater-Koster',
            'Excited states: ExcitedStateMethodology → GW, BSE',
            'Screening for many-body methods',
            'CoreHoleSpectra for X-ray spectroscopy',
            'DMFT for strongly correlated systems',
            'Method contributions and references between methods',
        ],
        'out_of_scope': [
            'Numerical settings like meshes and basis sets (see numerical_settings)',
            'Output properties computed by these methods (see output verticals)',
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
        'out_of_scope': [
            'Methods that use these settings (see model_method)',
            'Systems these apply to (see model_system)',
        ],
    },
    # =========================================================================
    # OUTPUTS TREE
    # =========================================================================
    'outputs': {
        'title': 'Outputs Base',
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
        'out_of_scope': [
            'Specific property types (see specialized verticals)',
            'Electronic structure properties (see electronic_properties)',
            'Many-body properties (see manybody_properties)',
            'Spectroscopic properties (see spectroscopy)',
            'Thermodynamic properties (see thermodynamics)',
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
        'out_of_scope': [
            "Many-body properties like Green's functions (see manybody_properties)",
            'Spectroscopic properties (see spectroscopy)',
            'Thermodynamic properties (see thermodynamics)',
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
        'out_of_scope': [
            'Methods that compute these (GW, BSE, DMFT in model_method)',
            'Basic electronic properties (see electronic_properties)',
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
        'out_of_scope': [
            'Methods that compute spectra (BSE, CoreHoleSpectra in model_method)',
            'DOS profiles (see electronic_properties)',
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
        'out_of_scope': [
            'Electronic structure properties (see electronic_properties)',
            'Spectroscopic properties (see spectroscopy)',
        ],
    },
}
