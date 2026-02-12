import os
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest
import structlog
from nomad.datamodel import EntryArchive
from nomad.units import ureg
from structlog.testing import LogCapture

from nomad_simulations.schema_packages.atoms_state import (
    AtomsState,
    BaseSpinOrbitalState,
    ElectronicState,
    SphericalSymmetryState,
)
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem, Representation
from nomad_simulations.schema_packages.numerical_settings import (
    KLinePath as KLinePathSettings,
)
from nomad_simulations.schema_packages.numerical_settings import KMesh as KMeshSettings
from nomad_simulations.schema_packages.numerical_settings import KSpace, SelfConsistency
from nomad_simulations.schema_packages.outputs import Outputs, SCFOutputs
from nomad_simulations.schema_packages.properties import (
    DOSProfile,
    ElectronicBandGap,
    ElectronicBandStructure,
    ElectronicDensityOfStates,
)
from nomad_simulations.schema_packages.variables import Energy2 as Energy
from nomad_simulations.schema_packages.variables import KLinePath

from . import logger

if os.getenv('_PYTEST_RAISE', '0') != '0':

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value


def generate_simulation(
    model_system: list[ModelSystem] = [],
    model_method: list[ModelMethod] = [],
    outputs: list[Outputs] = [],
) -> Simulation:
    """
    Generate a `Simulation` section with the main sub-sections, `ModelSystem`, `ModelMethod`, and `Outputs`.
    """
    return Simulation(
        model_method=model_method,
        model_system=model_system,
        outputs=outputs,
    )


def generate_model_system(
    system_type: str | None = None,
    positions: list[list[float]] | None = None,
    lattice_vectors: list[list[float]] | None = None,
    chemical_symbols: list[str] | None = None,
    orbitals_symbols: list[list[str]] | None = None,
    is_representative: bool | None = None,
    pbc: list[bool] | None = None,
    representation_name: str | None = None,
) -> ModelSystem | None:
    """
    Generate a `ModelSystem` section with the given parameters.
    All parameters are optional and will only be set if explicitly provided.
    Default values are not automatically applied.
    """
    if (
        chemical_symbols is not None
        and orbitals_symbols is not None
        and len(chemical_symbols) != len(orbitals_symbols)
    ):
        return None

    # Create model system with only provided values
    model_system_kwargs: dict[str, Any] = {}
    if system_type is not None:
        model_system_kwargs['type'] = system_type
    if is_representative is not None:
        model_system_kwargs['is_representative'] = is_representative

    model_system = ModelSystem(**model_system_kwargs)

    # Set positions if provided
    if positions is not None:
        model_system.positions = np.array(positions) * ureg.angstrom

    # Create representation with only provided values
    representation_kwargs: dict = {}
    if lattice_vectors is not None:
        representation_kwargs['lattice_vectors'] = (
            np.array(lattice_vectors) * ureg.angstrom
        )
    if pbc is not None and all(isinstance(x, bool) for x in pbc):
        representation_kwargs['periodic_boundary_conditions'] = pbc
    if representation_name is not None:
        representation_kwargs['name'] = representation_name

    # Only append representation if we have at least one parameter
    if representation_kwargs:
        model_system.representations.append(Representation(**representation_kwargs))

    # Add atoms_state to the model_system using ElectronicState with basis_orbitals
    if chemical_symbols is not None and orbitals_symbols is not None:
        atoms_state = []
        for element, orbitals in zip(chemical_symbols, orbitals_symbols):
            basis_list: list[SphericalSymmetryState] = []
            for o in orbitals:
                # Map common orbital labels like 's', 'px', 'py', 'pz', 'xy', 'xz', 'z^2', 'yz', 'x^2-y^2'
                l_symbol_to_number = {'s': 0, 'p': 1, 'd': 2, 'f': 3}
                ml_p_symbols = {'x': -1, 'z': 0, 'y': 1}
                ml_d_symbols = {'xy': -2, 'xz': -1, 'z^2': 0, 'yz': 1, 'x^2-y^2': 2}

                if o in {'s', 'p', 'd', 'f'}:
                    state = SphericalSymmetryState()
                    state.l_quantum_number = l_symbol_to_number[o]
                else:
                    # split into l-symbol and ml-symbol when possible
                    # p-orbitals: px, py, pz
                    if o in {'px', 'py', 'pz'}:
                        state = SphericalSymmetryState()
                        state.l_quantum_number = 1  # p
                        state.ml_quantum_number = ml_p_symbols[o[-1]]
                    elif o in {'xy', 'xz', 'z^2', 'yz', 'x^2-y^2'}:
                        state = SphericalSymmetryState()
                        state.l_quantum_number = 2  # d
                        state.ml_quantum_number = ml_d_symbols[o]
                    else:
                        # Fallback: default to s
                        state = SphericalSymmetryState()
                        state.l_quantum_number = 0  # s
                basis_list.append(state)

            e_state = ElectronicState()
            for bo in basis_list:
                e_state.basis_orbitals.append(bo)

            atom_state = AtomsState(chemical_symbol=element)
            atom_state.electronic_state = e_state
            atom_state.normalize(EntryArchive(), logger)
            atoms_state.append(atom_state)

        for state in atoms_state:
            model_system.particle_states.append(state)
    return model_system


def generate_scf_electronic_band_gap_template(
    n_scf_steps: int = 5,
    threshold_change: float | None = 1e-3,
    threshold_change_unit: str | None = 'joule',
) -> SCFOutputs:
    """
    Generate a `SCFOutputs` section with a template for the electronic_band_gap property.
    """
    scf_outputs = SCFOutputs()
    # Define a list of scf_steps with values of the total energy like [1, 1.1, 1.11, 1.111, etc],
    # such that the difference between one step and the next one decreases a factor of 10.
    value = None
    for i in range(n_scf_steps):
        value = 1 + sum([1 / (10**j) for j in range(1, i + 2)])
        scf_step = Outputs(electronic_band_gaps=[ElectronicBandGap(value=value)])
        scf_outputs.scf_steps.append(scf_step)
    # Add a SCF calculated PhysicalProperty
    if value is not None:
        scf_outputs.electronic_band_gaps.append(ElectronicBandGap(value=value))
    else:
        scf_outputs.electronic_band_gaps.append(ElectronicBandGap())
    # and a `SelfConsistency` ref section
    if threshold_change is not None:
        model_method = ModelMethod(
            numerical_settings=[
                SelfConsistency(
                    threshold_change=threshold_change,
                    threshold_change_unit=threshold_change_unit,
                )
            ]
        )
        simulation = generate_simulation(
            model_method=[model_method], outputs=[scf_outputs]
        )
        scf_outputs.electronic_band_gaps[
            0
        ].self_consistency_ref = simulation.model_method[0].numerical_settings[0]
    return scf_outputs


def generate_simulation_electronic_dos(
    energy_points: list[int] = [-3, -2, -1, 0, 1, 2, 3],
) -> Simulation:
    """
    Generate a `Simulation` section with an `ElectronicDensityOfStates` section under `Outputs`. It uses
    the template of the model_system created with the `generate_model_system` function.
    """
    # Create the `Simulation` section to make refs work
    model_system = generate_model_system(
        representation_name='original',
        system_type='bulk',
        positions=[[0, 0, 0], [0.5, 0.5, 0.5]],
        lattice_vectors=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        chemical_symbols=['Ga', 'As'],
        orbitals_symbols=[['s'], ['px', 'py']],
        is_representative=True,
        pbc=[False, False, False],
    )
    outputs = Outputs()
    simulation = generate_simulation(model_system=[model_system], outputs=[outputs])

    outputs.normalize(EntryArchive(), logger)

    # Populating the `ElectronicDensityOfStates` section
    variables_energy = Energy(points=energy_points * ureg.joule)
    electronic_dos = ElectronicDensityOfStates(energies=variables_energy)
    outputs.electronic_dos.append(electronic_dos)
    # Build ElectronicState sub_states for specific orbitals and add them to AtomsState
    ga_atom = model_system.particle_states[0]
    as_atom = model_system.particle_states[1]

    # Create sub_states for Ga atom orbitals (s)
    ga_s_basis = ga_atom.electronic_state.basis_orbitals[0]
    es_ga_s = ElectronicState(spin_orbit_state=ga_s_basis)
    ga_atom.electronic_state.sub_states.append(es_ga_s)
    es_ga_s.normalize(EntryArchive(), logger)

    # Create sub_states for As atom orbitals (px, py)
    as_px_basis = as_atom.electronic_state.basis_orbitals[0]
    es_as_px = ElectronicState(spin_orbit_state=as_px_basis)
    as_atom.electronic_state.sub_states.append(es_as_px)
    es_as_px.normalize(EntryArchive(), logger)

    as_py_basis = as_atom.electronic_state.basis_orbitals[1]
    es_as_py = ElectronicState(spin_orbit_state=as_py_basis)
    as_atom.electronic_state.sub_states.append(es_as_py)
    es_as_py.normalize(EntryArchive(), logger)

    # Normalize the top-level ElectronicState to set their names
    ga_atom.electronic_state.normalize(EntryArchive(), logger)
    as_atom.electronic_state.normalize(EntryArchive(), logger)

    orbital_s_Ga_pdos = DOSProfile(
        energies=variables_energy,
        entity_ref=es_ga_s,
    )
    orbital_px_As_pdos = DOSProfile(
        energies=variables_energy,
        entity_ref=es_as_px,
    )
    orbital_py_As_pdos = DOSProfile(
        energies=variables_energy,
        entity_ref=es_as_py,
    )
    orbital_s_Ga_pdos.value = [0.2, 0.5, 0, 0, 0, 0.0, 0.0] * ureg('1/joule')
    orbital_px_As_pdos.value = [1.0, 0.2, 0, 0, 0, 0.3, 0.0] * ureg('1/joule')
    orbital_py_As_pdos.value = [0.3, 0.5, 0, 0, 0, 0.5, 1.3] * ureg('1/joule')
    electronic_dos.projected_dos = [
        orbital_s_Ga_pdos,
        orbital_px_As_pdos,
        orbital_py_As_pdos,
    ]
    return simulation


def generate_k_line_path(
    high_symmetry_path_names: list[str] = ['Gamma', 'X', 'Y', 'Gamma'],
    high_symmetry_path_values: list[list[float]] = [
        [0, 0, 0],
        [0.5, 0, 0],
        [0, 0.5, 0],
        [0, 0, 0],
    ],
) -> KLinePathSettings:
    return KLinePathSettings(
        high_symmetry_path_names=high_symmetry_path_names,
        high_symmetry_path_values=high_symmetry_path_values,
    )


def generate_k_space_simulation(
    system_type: str = 'bulk',
    is_representative: bool = True,
    positions: list[list[float]] = [[0, 0, 0], [0.5, 0.5, 0.5]],
    lattice_vectors: list[list[float]] = [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    chemical_symbols: list[str] = ['Ga', 'As'],
    orbitals_symbols: list[list[str]] = [['s'], ['px', 'py']],
    pbc: list[bool] = [False, False, False],
    reciprocal_lattice_vectors: list[list[float]] | None = [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
    ],
    high_symmetry_path_names: list[str] = ['Gamma', 'X', 'Y', 'Gamma'],
    high_symmetry_path_values: list[list[float]] = [
        [0, 0, 0],
        [0.5, 0, 0],
        [0, 0.5, 0],
        [0, 0, 0],
    ],
    klinepath_points: list[float] | None = None,
    grid=[6, 6, 6],
) -> Simulation:
    model_system = generate_model_system(
        representation_name='primitive',
        system_type=system_type,
        is_representative=is_representative,
        positions=positions,
        lattice_vectors=lattice_vectors,
        chemical_symbols=chemical_symbols,
        orbitals_symbols=orbitals_symbols,
        pbc=pbc,
    )
    k_space = KSpace()
    # adding `reciprocal_lattice_vectors`
    if reciprocal_lattice_vectors is not None:
        k_space.reciprocal_lattice_vectors = (
            2 * np.pi * np.array(reciprocal_lattice_vectors) / ureg.angstrom
        )
    # adding `KMeshSettings
    k_mesh = KMeshSettings(grid=grid)
    k_space.k_mesh.append(k_mesh)
    # adding `KLinePathSettings`
    k_line_path = KLinePathSettings(
        high_symmetry_path_names=high_symmetry_path_names,
        high_symmetry_path_values=high_symmetry_path_values,
    )
    if klinepath_points is not None:
        k_line_path.points = klinepath_points
    k_space.k_line_path = k_line_path
    # appending `KSpace` to `ModelMethod.numerical_settings`
    model_method = ModelMethod()
    model_method.numerical_settings.append(k_space)
    return generate_simulation(model_method=[model_method], model_system=[model_system])


def generate_electronic_band_structure(
    reciprocal_lattice_vectors: list[list[float]] | None = [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
    ],
    value: list | None = [
        [3, -2],
        [3, 1],
        [4, -2],
        [5, -1],
        [4, 0],
        [2, 0],
        [2, 1],
        [4, -3],
    ],
    occupation: list | None = [
        [0, 2],
        [0, 1],
        [0, 2],
        [0, 2],
        [0, 1.5],
        [0, 1.5],
        [0, 1],
        [0, 2],
    ],
    highest_occupied: float | None = None,
    lowest_unoccupied: float | None = None,
) -> ElectronicBandStructure:
    """
    Generate an `ElectronicBandStructure` section with the given parameters.
    """
    outputs = Outputs()
    k_space = KSpace(
        k_line_path=KLinePathSettings(
            points=[
                [0, 0, 0],
                [1, 0, 0],
                [0, 1, 0],
                [0, 0, 1],
                [1, 1, 0],
                [1, 0, 1],
                [0, 1, 1],
                [1, 1, 1],
            ]
        )
    )
    model_method = ModelMethod(numerical_settings=[k_space])
    if reciprocal_lattice_vectors:
        k_space.reciprocal_lattice_vectors = reciprocal_lattice_vectors
    _ = generate_simulation(
        model_system=[
            generate_model_system(
                representation_name='original',
                system_type='bulk',
                positions=[[0, 0, 0], [0.5, 0.5, 0.5]],
                lattice_vectors=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                chemical_symbols=['Ga', 'As'],
                orbitals_symbols=[['s'], ['px', 'py']],
                is_representative=True,
                pbc=[False, False, False],
            )
        ],
        model_method=[model_method],
        outputs=[outputs],
    )
    electronic_band_structure = ElectronicBandStructure(n_levels=2)
    outputs.electronic_eigenvalues = [electronic_band_structure]
    electronic_band_structure.k_path = KLinePath(
        points=model_method.numerical_settings[0].k_line_path
    )
    if value is not None:
        electronic_band_structure.value = value
    if occupation is not None:
        electronic_band_structure.occupation = occupation
    electronic_band_structure.highest_occupied = highest_occupied
    electronic_band_structure.lowest_unoccupied = lowest_unoccupied
    return electronic_band_structure


@pytest.fixture(scope='session')
def model_system() -> ModelSystem:
    return generate_model_system(
        representation_name='original',
        system_type='bulk',
        positions=[[0, 0, 0], [0.5, 0.5, 0.5]],
        lattice_vectors=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        chemical_symbols=['Ga', 'As'],
        orbitals_symbols=[['s'], ['px', 'py']],
        is_representative=True,
        pbc=[False, False, False],
    )


@pytest.fixture(scope='session')
def scf_electronic_band_gap() -> SCFOutputs:
    return generate_scf_electronic_band_gap_template()


@pytest.fixture(scope='session')
def simulation_electronic_dos() -> Simulation:
    return generate_simulation_electronic_dos()


@pytest.fixture(scope='session')
def k_line_path() -> KLinePathSettings:
    return generate_k_line_path()


@pytest.fixture(scope='session')
def k_space_simulation() -> Simulation:
    return generate_k_space_simulation()


refs_apw = [
    {
        'm_def': 'nomad_simulations.schema_packages.basis_set.BasisSetContainer',
    },
    {
        'm_def': 'nomad_simulations.schema_packages.basis_set.BasisSetContainer',
        'basis_set_components': [
            {
                'm_def': 'nomad_simulations.schema_packages.basis_set.APWPlaneWaveBasisSet',
                'cutoff_energy': 500.0,
            },
        ],
    },
    {
        'm_def': 'nomad_simulations.schema_packages.basis_set.BasisSetContainer',
        'basis_set_components': [
            {
                'm_def': 'nomad_simulations.schema_packages.basis_set.APWPlaneWaveBasisSet',
                'cutoff_energy': 500.0,
            },
            {
                'm_def': 'nomad_simulations.schema_packages.basis_set.MuffinTinRegion',
                'species_scope': ['/data/model_system/0/particle_states/0'],
                'radius': 1.0,
                'l_max': 2,
                'l_channels': [
                    {
                        'name': 0,
                        'orbitals': [
                            {
                                'm_def': 'nomad_simulations.schema_packages.basis_set.APWOrbital',
                                'energy_parameter': [0.0],
                                'differential_order': [0],
                            },
                        ],
                    },
                    {
                        'name': 1,
                        'orbitals': [
                            {
                                'm_def': 'nomad_simulations.schema_packages.basis_set.APWOrbital',
                                'energy_parameter': [0.0],
                                'differential_order': [0],
                            },
                        ],
                    },
                    {
                        'name': 2,
                        'orbitals': [
                            {
                                'm_def': 'nomad_simulations.schema_packages.basis_set.APWOrbital',
                                'energy_parameter': [0.0],
                                'differential_order': [0],
                            },
                        ],
                    },
                ],
            },
        ],
    },
]


@pytest.fixture
def log_output():
    capture = LogCapture()
    processors = structlog.get_config()['processors']
    old_processors = processors.copy()
    try:
        # clear processors list and use LogCapture for testing
        processors.clear()
        processors.append(capture)
        structlog.configure(processors=processors)
        yield capture
    finally:
        # remove LogCapture and restore original processors
        processors.clear()
        processors.extend(old_processors)
        structlog.configure(processors=processors)


@pytest.fixture
def approx():
    def func(expected, abs: float = 0.0, rel=1e-6):
        return pytest.approx(expected, abs=abs, rel=rel)

    return func


def make_spherical_state(
    n: int | None = 1,
    lqn: int | None = 0,
    ml: int | None = None,
    j: float | None = None,
    kappa: int | None = None,
    s: float | None = None,
    ms: float | None = None,
    coupling_origin: str | None = None,
) -> SphericalSymmetryState:
    """
    Construct a SphericalSymmetryState with convenient aliases for quantum numbers.

    Parameters map to schema quantities:
    - n -> n_quantum_number
    - lqn -> l_quantum_number
    - ml -> ml_quantum_number
    - j -> j_quantum_number (float)
    - kappa -> kappa_quantum_number
    - s -> s_quantum_number
    - ms -> ms_quantum_number
    - coupling_origin -> coupling_origin (e.g., 'pure_LS','pure_jj','intermediate','relativistic')
    """
    state = SphericalSymmetryState()
    if n is not None:
        state.n_quantum_number = n
    if lqn is not None:
        state.l_quantum_number = lqn
    if ml is not None:
        state.ml_quantum_number = ml
    if j is not None:
        state.j_quantum_number = j
    if kappa is not None:
        state.kappa_quantum_number = kappa
    if s is not None:
        state.s_quantum_number = s
    if ms is not None:
        state.ms_quantum_number = ms
    if coupling_origin is not None:
        state.coupling_origin = coupling_origin
    return state


def make_electronic_state(
    basis_orbitals: list[BaseSpinOrbitalState] | None = None,
    *,
    name: str | None = None,
    symmetry_label: str | None = None,
    point_group: str | None = None,
    occupation: float | None = None,
    spin_orbit: BaseSpinOrbitalState | None = None,
    sub_states: list[ElectronicState] | None = None,
) -> ElectronicState:
    """
    Construct an ElectronicState, optionally with a list of basis_orbitals and other metadata.

    - basis_orbitals: list of BaseSpinOrbitalState (e.g., SphericalSymmetryState) to define expansion basis
    - name, symmetry_label, point_group, occupation: metadata
    - spin_orbit: optional BaseSpinOrbitalState to assign to spin_orbit_state subsection
    - sub_states: optional child ElectronicState hierarchy to append to sub_states
    """
    es = ElectronicState()
    if name is not None:
        es.name = name
    if symmetry_label is not None:
        es.symmetry_label = symmetry_label
    if point_group is not None:
        es.point_group = point_group
    if occupation is not None:
        es.occupation = occupation

    if spin_orbit is not None:
        es.spin_orbit_state = spin_orbit

    if basis_orbitals:
        for bo in basis_orbitals:
            es.basis_orbitals.append(bo)

    if sub_states:
        for child in sub_states:
            es.sub_states.append(child)

    return es
