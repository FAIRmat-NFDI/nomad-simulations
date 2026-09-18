from nomad.datamodel import EntryArchive
from nomad.metainfo import Quantity, SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .general import (
    INCORRECT_N_TASKS,
    SimulationWorkflow,
    SimulationWorkflowMethod,
    SimulationWorkflowResults,
)

m_package = SchemaPackage()


class SinglePointMethod(SimulationWorkflowMethod):
    """
    Contains definitions for the input model of a single point workflow.

    The self-consistent field (SCF) loop that produces a single point is controlled by the
    input settings below. They mirror `GeometryOptimizationMethod.optimization_method` and
    `n_steps_maximum` for the SCF loop: `scf_minimization_algorithm` names the algorithm and
    `n_max_iterations` bounds the iteration count. The per-property convergence thresholds
    themselves (formerly `SelfConsistency.threshold_change`) are carried by
    `convergence_targets` (see `WorkflowConvergenceTarget` and its subclasses). Together these
    absorb the deprecated `SelfConsistency(NumericalSettings)` section.
    """

    _label = 'Single point model'

    scf_minimization_algorithm = Quantity(
        type=str,
        shape=[],
        description="""
        The algorithm used to minimize the energy in the self-consistent field (SCF) loop.
        Counterpart of `GeometryOptimizationMethod.optimization_method` for the SCF loop.
        """,
    )

    n_max_iterations = Quantity(
        type=int,
        shape=[],
        description="""
        Maximum number of allowed self-consistent field (SCF) iterations. Counterpart of
        `GeometryOptimizationMethod.n_steps_maximum` for the SCF loop; the SCF is not
        considered converged once this bound is reached. The per-property convergence
        thresholds are carried by `convergence_targets`.
        """,
    )


class SinglePointResults(SimulationWorkflowResults):
    """
    Contains defintions for the results of a single point workflow.
    """

    _label = 'Single point results'


class SinglePoint(SimulationWorkflow):
    """
    Definitions for single point workflow.
    """

    _task_label = 'Calculation'

    method = SubSection(sub_section=SinglePointMethod.m_def)

    results = SubSection(sub_section=SinglePointResults.m_def)

    @log
    def map_inputs(self, archive: EntryArchive):
        if not self.method:
            self.method = SinglePointMethod()

        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive):
        if not self.results:
            self.results = SinglePointResults()

        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)
        if len(self.tasks) != 1:
            logger.error(INCORRECT_N_TASKS)
            return
        self.tasks[0].name = self._task_label

        # add inputs to calculation inputs
        self.tasks[0].inputs.extend(
            [inp for inp in self.inputs if inp not in self.tasks[0].inputs]
        )

        # add outputs of calculation to outputs
        self.outputs.extend(
            [out for out in self.tasks[0].outputs if out not in self.outputs]
        )


m_package.__init_metainfo__()
