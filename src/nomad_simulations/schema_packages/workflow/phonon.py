from nomad.datamodel import ArchiveSection, EntryArchive
from nomad.datamodel.metainfo.workflow import Link, TaskReference
from nomad.metainfo import MEnum, Quantity, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.utils import log

from .general import (
    INCORRECT_N_TASKS,
    SimulationWorkflow,
    SimulationWorkflowMethod,
    SimulationWorkflowResults,
    WorkflowConvergenceTarget,
)


class FiniteDifferenceMethod(ArchiveSection):
    
    displacement = Quantity(
        type=float,
        description="""
        Magnitude of the displacement applied to atoms.
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


class DFPTMethod(ArchiveSection):
    
    q_mesh = Quantity(
        type=int,
        shape=[3],
        unit='1 / meter ** 3',
        description="""
        Number of q-points in each direction in reciprocal space.
        """
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

    # TODO This can be populated by the normalizer
    method = Quantity(
        type=MEnum('finite_differences', 'DFPT'),
        description="""
        Method that was used to compute phonons. 
        Options: 
            - 'finite_differences': Series of calculations with dislocated atoms in a supercell in real space.
            - 'DFPT': Density-functional perturbation theory, solution of the Sternheimer equations in reciprocal space.
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

class FiniteDifferenceResults(ArchiveSection):

    n_displacements = Quantity(
        type=int,
        shape=[],
        description="""
        Number of independent displacements.
        """,
    )

    # TODO This is a repetition here - it needs to be read from PhononResults instead (?)
    n_atoms = Quantity(
        type=int,
        shape=[],
        description="""
        Number of atoms in the simulation cell.
        """,
    )

    displacements = Quantity(
        type=float,
        shape=['n_displacements', 'n_atoms', 3],
        unit='meter',
        description="""
        Value of the displacements applied to each atom in the simulation cell.
        """,
    )

class DFPTResults(ArchiveSection):

    perturbed_potential = Quantity(
        description="""
        Perturbed potential as obtained from the DFPT calculation.
        """
    )


class PhononResults(SimulationWorkflowResults):
    _label = 'Phonon results'

    n_imaginary_frequencies = Quantity(
        type=int,
        shape=[],
        description="""
        Number of modes with imaginary frequencies.
        """,
    )

    n_bands = Quantity(
        type=int,
        shape=[],
        description="""
        Number of phonon bands.
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

    group_velocity = Quantity(
        type=float,
        shape=['n_qpoints', 'n_bands', 3],
        unit='meter / second',
        description="""
        Calculated value of the group velocity at each qpoint.
        """,
    )

    n_atoms = Quantity(
        type=int,
        shape=[],
        description="""
        Number of atoms in the simulation cell.
        """,
    )

    # TODO verify the shape
    interatomic_force_constants = Quantity(
        type=float,
        shape=[3 * 'n_atoms', 3 * 'n_atoms'],
        description = """
        Second derivatives of the total energy with respect to the Cartesian displacements of two atoms. 
        """
    )

    dynamical_tensor = Quantity(
        type=float,
        shape=['n_qpoints', 3, 3],
        description="""
        Mass-weighted force-constant matrix that governs how the lattice responds to infinitesimal atomic displacements.
        """
    )

    ewald_parameter = Quantity(
        type=float,
        description="""
        Controls how the Coulombic (or dipolar) interaction is partitioned between long- and short-range contributions.
        """
    )

    # TODO BEC can be obtained both by derivatives of the forces w.r.t. the energy, or from the polarizability w.r.t. the displacement.
    # If the calculation is converged, both should be identical - this can be used as a measure of quality for the result.
    born_effective_charges = Quantity(
        type=float,
        shape=['n_atoms', 3, 3],
        description="""
        Born-effective charges obtained from an electronic-structure calculation.
        """
    )

    # TODO verify shape
    gauge = Quantity(
        type=float,
        shape=[3],
        description="""
        Gauge that is applied to the eigenvectors, typically such that the first eigenvector is real. 
        """
    )

    # TODO add dos and bandstructure - implement properties in properties.band_structure and properites.spectral_profile

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

    _task_label = 'Force calculation'

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
