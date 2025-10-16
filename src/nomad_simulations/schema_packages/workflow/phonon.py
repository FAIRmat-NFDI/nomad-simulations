from nomad.datamodel import EntryArchive
from nomad.datamodel.metainfo.workflow import Link, TaskReference
from nomad.metainfo import Quantity
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .general import (
    INCORRECT_N_TASKS,
    SimulationWorkflow,
    SimulationWorkflowModel,
    SimulationWorkflowResults,
)


class PhononModel(SimulationWorkflowModel):
    _label = 'Phonon calculation parameters'

    force_calculator = Quantity(
        type=str,
        shape=[],
        description="""
        Name of the program used to calculate the forces.
        """,
    )

    phonon_calculator = Quantity(
        type=str,
        shape=[],
        description="""
        Name of the program used to perform phonon calculation.
        """,
    )

    mesh_density = Quantity(
        type=float,
        shape=[],
        unit='1 / meter ** 3',
        description="""
        Density of the k-mesh for sampling.
        """,
    )

    random_displacements = Quantity(
        type=bool,
        shape=[],
        description="""
        Identifies if displacements are made randomly.
        """,
    )

    with_non_analytic_correction = Quantity(
        type=bool,
        shape=[],
        description="""
        Identifies if non-analytical term corrections are applied to dynamical matrix.
        """,
    )

    with_grueneisen_parameters = Quantity(
        type=bool,
        shape=[],
        description="""
        Identifies if Grueneisen parameters are calculated.
        """,
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

    n_displacements = Quantity(
        type=int,
        shape=[],
        description="""
        Number of independent displacements.
        """,
    )

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

    # TODO add band dos and bandstructure


class Phonon(SimulationWorkflow):
    """
    Definitions for a phonon workflow.
    """

    _task_label = 'Force calculation'

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = PhononModel()
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
