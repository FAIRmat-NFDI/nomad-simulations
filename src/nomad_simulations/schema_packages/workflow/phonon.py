from nomad.datamodel import ArchiveSection, EntryArchive
from nomad.datamodel.metainfo.workflow import Link, TaskReference
from nomad.metainfo import MEnum, Quantity, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.properties.lattice_dynamics import (
    BornEffectiveCharges,
    DynamicalMatrix,
    InfiniteFrequencyDielectricMatrix,
    InteratomicForceConstants,
    PhononBandStructure,
    PhononDensityOfStates,
)
from nomad_simulations.schema_packages.properties.thermodynamics import HeatCapacity
from nomad_simulations.schema_packages.utils import log

from .general import (
    INCORRECT_N_TASKS,
    SimulationWorkflow,
    SimulationWorkflowMethod,
    SimulationWorkflowResults,
    WorkflowConvergenceTarget,
)


class FiniteDifferenceMethod(ArchiveSection):
    displacement_value = Quantity(
        type=float,
        shape=[1],
        unit='meter',
        description="""
        Value of the displacements applied to each atom in the simulation cell.
        """,
    )

    n_displacements = Quantity(
        type=int,
        shape=[1],
        description="""
        Number of independent displacements.
        """,
    )

    displacements = Quantity(
        type=float,
        shape=[],
        unit='meter',
        description="""
        Value of the displacements applied to each atom in the simulation cell.
        """,
    )

    supercell_size = Quantity(
        type=int,
        shape=[3],
        description="""
        Size of the supercell that is used in the calculation.
        """,
    )

    force_calculator = SubSection(sub_section=ModelMethod.m_def, repeats=False)

    random_displacements = Quantity(
        type=bool,
        shape=[],
        description="""
        Identifies if displacements are made randomly.
        """,
    )

    # TODO move to SimulationWorkflowMethod? - it is also used in geometry optimization workflows
    # in cases where the workflow has no individual targets, it will not be populated
    single_point_convergence_targets = SubSection(
        sub_section=WorkflowConvergenceTarget.m_def,
        repeats=True,
        description="""
        SCF convergence targets applied to each task, i.e., displacement.
        """,
    )

    mesh_density = Quantity(
        type=float,
        shape=[3],
        unit='1 / meter ** 3',
        description="""
        Density of the k-mesh for sampling.
        """,
    )

    # TODO need specification
    has_temperature_depended_force_constants = Quantity(
        type=bool,
        description="""
        Temperature dependent force constants are considered in this calculation.
        """,
    )


class DFPTMethod(ArchiveSection):
    q_mesh = Quantity(
        type=int,
        shape=[3],
        unit='1 / meter ** 3',
        description="""
        Number of q-points in each direction in reciprocal space.
        """,
    )
    # The convergene threshold for the Sternheimer equation is represented by an EnergyConvergenceTarget in SimulationWorkflowMethod.


class PhononMethod(SimulationWorkflowMethod):
    _label = 'Phonon calculation parameters'

    program_name = Quantity(
        type=str,
        shape=[],
        description="""
        Name of the program used to perform phonon calculation.
        """,
    )

    finite_differences_method = SubSection(
        sub_section=FiniteDifferenceMethod.m_def,
        repeats=False,
        description="""
        Method details for finite-differences calculations.
        """,
    )

    dfpt_method = SubSection(
        sub_section=DFPTMethod.m_def,
        repeats=False,
        description="""
        Method details for DFPT calculations.
        """,
    )

    atomic_masses = Quantity(
        type=float,
        shape=[],
        description="""
        Atomic masses used in the calculation. Depends on the used isotope of the elements.
        """,
    )

    n_qpoints = Quantity(
        type=int,
        shape=[],
        description="""
        Number of q points for which phonon properties are evaluated.
        """,
    )

    qpoints = Quantity(
        type=float,
        shape=['n_qpoints', 3],
        description="""
        Value of the qpoints.
        """,
    )


class PhononResults(SimulationWorkflowResults):
    _label = 'Phonon results'

    group_velocity = Quantity(
        type=float,
        shape=['n_qpoints', 'n_bands', 3],
        unit='meter / second',
        description="""
        Calculated value of the group velocity at each qpoint.
        """,
    )

    interatomic_force_constants = SubSection(
        sub_section=InteratomicForceConstants.m_def
    )

    dynamical_matrix = SubSection(sub_section=DynamicalMatrix.m_def)

    gauge = Quantity(
        type=float,
        shape=[],
        description="""
        Gauge that is applied to the eigenvectors, typically such that the first eigenvector is real.
        """,
    )

    density_of_states = SubSection(sub_section=PhononDensityOfStates.m_def)

    band_structure = SubSection(sub_section=PhononBandStructure.m_def)

    heat_capacity = SubSection(sub_section=HeatCapacity.m_def)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)

        # compute band structure and density of states
        # apply transformations to obtain interatomic force constants from dynamical tensor, or vice versa
        # TODO implement
        pass


class Phonon(SimulationWorkflow):
    """
    Definitions for a phonon workflow.
    """

    _task_label = 'Phonon calculation'

    # TODO This can be populated by the normalizer
    approach = Quantity(
        type=MEnum('finite_differences', 'DFPT'),
        description="""
        Approach that was used to compute phonons.
        Options:
            - 'finite_differences': Series of calculations with dislocated atoms in a supercell in real space.
            - 'DFPT': Density-functional perturbation theory, solution of the Sternheimer equations in reciprocal space.
        """,
    )

    born_effective_charges = SubSection(
        sub_section=BornEffectiveCharges.m_def,
        repeats=True,
        description="""
        The BEC can be obtained both by derivatives of the forces w.r.t. the energy, or from the polarizability w.r.t. the displacement. If the calculation is converged, both should be identical - this can be used as a measure of quality for the result.
        """,
    )
    infinite_frequency_dielectric_matrix = SubSection(
        sub_section=InfiniteFrequencyDielectricMatrix.m_def
    )

    method = SubSection(sub_section=PhononMethod.m_def)

    results = SubSection(sub_section=PhononResults.m_def)

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.method:
            self.method = PhononMethod()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = PhononResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)

        if len(self.tasks) < 2:
            logger.error(INCORRECT_N_TASKS)
            return

        # assign inputs to force calculations
        for n, task in enumerate(self.tasks[:-1]):
            if not task.name:
                task.name = f'Force calculation for supercell {n}'
            task.inputs.extend([inp for inp in self.inputs if inp not in task.inputs])

        # assign outputs of force calculation as input to phonon task
        self.tasks[-1].inputs = [
            Link(
                name='Linked task',
                section=task.task if isinstance(task, TaskReference) else task,
            )
            for task in self.tasks[:-1]
        ]

        # add phonon task oututs to outputs
        self.outputs.extend(
            [out for out in self.tasks[-1].outputs if out not in self.outputs]
        )

        if not self.tasks[-1].name:
            self.tasks[-1].name = 'Phonon calculation'
