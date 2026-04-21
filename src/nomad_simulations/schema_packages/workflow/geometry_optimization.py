import jmespath
import numpy as np
from nomad.datamodel import EntryArchive
from nomad.datamodel.metainfo.workflow import Link, Task
from nomad.metainfo import MEnum, Quantity, SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.properties.energies import BaseEnergy
from nomad_simulations.schema_packages.utils import log

from .general import (
    SerialWorkflow,
    SimulationWorkflowMethod,
    SimulationWorkflowResults,
    WorkflowConvergenceTarget,
)
from .single_point import SinglePoint

m_package = SchemaPackage()


class GeometryOptimizationModel(SimulationWorkflowMethod):
    """
    Workflow model describing a geometry optimization.
    """

    label = 'Geometry optimization parameters'

    optimization_type = Quantity(
        type=MEnum('static', 'atomic', 'cell_shape', 'cell_volume'),
        shape=[],
        description="""
        The type of geometry optimization, which denotes what is being optimized.

        Allowed values are:

        | Type                   | Description                               |

        | ---------------------- | ----------------------------------------- |

        | `"static"`             | no optimization |

        | `"atomic"`             | the atomic coordinates alone are updated |

        | `"cell_volume"`         | `"atomic"` + cell lattice parameters are updated isotropically |

        | `"cell_shape"`        | `"cell_volume"` but without the isotropic constraint: all cell parameters are updated |

        """,
    )

    optimization_method = Quantity(
        type=str,
        shape=[],
        description="""
        The method used for geometry optimization. Some known possible values are:
        `"steepest_descent"`, `"conjugate_gradient"`, `"low_memory_broyden_fletcher_goldfarb_shanno"`.
        """,
    )

    n_steps_maximum = Quantity(
        type=int,
        shape=[],
        description="""
        Maximum number of optimization steps.
        """,
    )

    sampling_frequency = Quantity(
        type=int,
        shape=[],
        description="""
        The number of optimization steps between saved outputs.
        """,
    )

    single_point_convergence_targets = SubSection(
        sub_section=WorkflowConvergenceTarget.m_def,
        repeats=True,
        description="""
        SCF convergence targets applied to each subtask (optimization step, MD frame, etc.).

        These targets check SCF convergence within each subtask of a composite workflow.
        For GeometryOptimization, this applies to each optimization step; for MolecularDynamics,
        this would apply to each MD frame; for Phonon, to each displacement calculation.

        During normalization, workflows create SinglePoint tasks for subtasks with SCF iterations,
        and each task evaluates these targets independently. Results are aggregated into
        `is_single_point_converged` via JMESPath: `workflow2.tasks[*].results.convergence[*].is_reached`.

        Common SCF convergence targets:
        - EnergyConvergenceTarget: SCF total energy convergence
        - PotentialConvergenceTarget: Effective potential convergence
        - ChargeConvergenceTarget: Charge density convergence

        Note: This field should conceptually be available on SimulationWorkflowMethod base class
        for any workflow with SCF subtasks, but is currently only implemented here. This is
        a known schema design limitation.

        See also:
        - `convergence_targets`: Workflow-level convergence (e.g., forces for geometry optimization)
        - `GeometryOptimizationResults.is_single_point_converged`: Aggregated SCF status
        """,
    )


# Backwards-compatible alias used across parser/tests.
class GeometryOptimizationMethod(GeometryOptimizationModel):
    pass


class GeometryOptimizationResults(SimulationWorkflowResults):
    _label = 'Geometry optimization results'

    # TODO: This should be an array with shape=['n_steps'] to report convergence
    # status per optimization step, rather than aggregating across all steps.
    # Current implementation collapses per-step information into single boolean.
    is_single_point_converged = Quantity(
        type=bool,
        description="""
        Aggregated SCF convergence status across all optimization steps.

        Returns True if all SCF runs in all optimization steps converged to their
        specified targets (defined in `method.single_point_convergence_targets`).
        Returns False if any SCF run failed to converge. Returns None if no
        convergence data is available.

        This value is computed during normalization by aggregating convergence results
        from all SinglePoint tasks using the JMESPath query:
        `workflow2.tasks[*].results.convergence[*].is_reached`

        The aggregation logic is: `all(all(step_results) for step_results in all_results)`

        Example:
            For a geometry optimization with 3 steps:
            - Step 0: [True, True] (2 SCF targets, both converged)
            - Step 1: [True, True]
            - Step 2: [True, False] (second target failed)
            → is_single_point_converged = False

        Note: This field currently provides only aggregate information. Per-step
        convergence status should be retrieved from individual task results:
        `workflow2.tasks[step_index].results.convergence`

        See also:
        - `method.single_point_convergence_targets`: SCF convergence criteria
        - `is_converged`: Geometry-level convergence status
        - `convergence`: Per-target geometry convergence results
        """,
    )
    n_steps = Quantity(
        type=int,
        shape=[],
        description="""
        Number of saved optimization steps.
        """,
    )

    energies = Quantity(
        type=np.float64,
        unit='joule',
        shape=['n_steps'],
        description="""
        List of energy_total values gathered from the single configuration
        calculations that are a part of the optimization trajectory.
        """,
    )

    steps = Quantity(
        type=np.int32,
        shape=['n_steps'],
        description="""
        The step index corresponding to each saved configuration.
        """,
    )

    final_energy_difference = Quantity(
        type=np.float64,
        shape=[],
        unit='joule',
        description="""
        The difference in the energy_total between the last two steps during
        optimization.
        """,
    )

    final_force_maximum = Quantity(
        type=np.float64,
        shape=[],
        unit='newton',
        description="""
        The maximum net force in the last optimization step.
        """,
    )

    final_displacement_maximum = Quantity(
        type=np.float64,
        shape=[],
        unit='meter',
        description="""
        The maximum displacement in the last optimization step with respect to previous.
        """,
    )

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.n_steps:
            self.n_steps = len(archive.data.outputs)

        if self.energies is None:
            energies_l = []
            for outputs in archive.data.outputs:
                try:
                    energies_l.append(outputs.total_energies[-1].value.magnitude)
                except Exception:
                    logger.error('Energy not found in outputs.')
                    energies_l = []
                    break
            if energies_l:
                energies = np.array(energies_l)
                self.energies = energies * BaseEnergy.value.unit
                # For single-step or flat trajectories there may be no non-zero energy delta.
                denergies = energies[1:] - energies[: len(energies) - 1]
                if len(denergies) > 0:
                    nonzero_indices = denergies.nonzero()[0]
                    if len(nonzero_indices) > 0:
                        self.final_energy_difference = (
                            denergies[nonzero_indices[-1]] * BaseEnergy.value.unit
                        )
        if self.final_force_maximum is None:
            final_forces = jmespath.search('data.outputs[-1].total_forces[-1]', archive)
            if final_forces is not None:
                force_abs = np.linalg.norm(final_forces.value, axis=1)
                self.final_force_maximum = max(force_abs)


class GeometryOptimization(SerialWorkflow):
    """
    Definitions for geometry optimization workflow.
    """

    _task_label = 'Step'

    method = SubSection(sub_section=GeometryOptimizationMethod.m_def)

    results = SubSection(sub_section=GeometryOptimizationResults.m_def)

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.method:
            self.method = GeometryOptimizationMethod()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = GeometryOptimizationResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    @log
    def map_tasks(self, archive: EntryArchive) -> None:
        """
        Generate tasks from archive data outputs. Tasks are ordered and linked based
        on the execution time of the calculation corresponding to the output.
        Falls back to model_system if outputs are not populated.
        """
        # Do not overwrite assigned tasks
        if self.tasks or not archive.data:
            return

        logger = self.map_tasks.__annotations__['logger']

        # Try primary path (outputs) first, then fallback to model_system
        if archive.data.outputs and len(archive.data.outputs) > 0:
            self._map_tasks_from_outputs(archive, logger)
        elif archive.data.model_system and len(archive.data.model_system) > 0:
            self._map_tasks_from_model_system(archive, logger)

    def _map_tasks_from_outputs(
        self, archive: EntryArchive, logger: BoundLogger
    ) -> None:
        """Create tasks from archive outputs with timing-based linking."""
        outputs = sorted(archive.data.outputs, key=lambda x: x.wall_start or 0)
        tasks = []
        parent_n = 0
        root_n = 0

        for n, output in enumerate(outputs):
            task = self._create_task_for_output(n, output, archive, logger)
            tasks.append(task)

            # Link tasks based on timing
            parent_n, root_n = self._link_task_by_timing(
                task, output, outputs, tasks, n, parent_n, root_n
            )

        self.tasks.extend(tasks)

    def _create_task_for_output(
        self, n: int, output, archive: EntryArchive, logger: BoundLogger
    ) -> Task:
        """Create appropriate task type (SinglePoint or generic Task) for an output."""
        task_name = f'{self._task_label} {n}'
        output_link = Link(name='Outputs', section=output)

        # Create SinglePoint task with convergence analysis if SCF steps present
        if output.get('scf_steps') is not None:
            task = SinglePoint(
                name=task_name,
                outputs=[output_link],
                results=SimulationWorkflowResults(),
            )
            self._add_convergence_to_task(task, archive, logger)
            return task

        # Otherwise create generic task
        return Task(name=task_name, outputs=[output_link])

    def _add_convergence_to_task(
        self, task: SinglePoint, archive: EntryArchive, logger: BoundLogger
    ) -> None:
        """Add convergence analysis to a SinglePoint task."""
        single_point_convergence = jmespath.search(
            'workflow2.method.single_point_convergence_targets', archive
        )
        if single_point_convergence is not None:
            convergence_result = task._resolve_convergence(
                archive, single_point_convergence, logger
            )
            task.results.convergence = convergence_result

    def _link_task_by_timing(
        self,
        task: Task,
        output,
        outputs: list,
        tasks: list[Task],
        n: int,
        parent_n: int,
        root_n: int,
    ) -> tuple[int, int]:
        """
        Link task to previous tasks based on execution timing.

        Returns:
            tuple[int, int]: Updated (parent_n, root_n) indices.
        """
        tstart = output.wall_start
        tend = outputs[parent_n].wall_end

        if tstart is None and tend is None:
            return parent_n, root_n

        if tstart >= tend:
            # Link to all tasks from parent to current (exclusive)
            task.inputs.extend(
                [Link(name='Linked task', section=t) for t in tasks[parent_n:n]]
            )
            return n, parent_n  # Update parent_n to current, root_n to old parent
        elif n != parent_n:
            # Link to all tasks from root to parent (exclusive)
            task.inputs.extend(
                [Link(name='Linked task', section=t) for t in tasks[root_n:parent_n]]
            )

        return parent_n, root_n

    def _map_tasks_from_model_system(
        self, archive: EntryArchive, logger: BoundLogger
    ) -> None:
        """Fallback: create tasks from model_system when outputs not available."""
        logger.info(
            'Creating tasks from model_system (outputs not available). '
            'Task convergence analysis will not be available.'
        )

        for n, model_system in enumerate(archive.data.model_system):
            task = Task(
                name=f'{self._task_label} {n}',
                outputs=[Link(name='Model System', section=model_system)],
            )
            self.tasks.append(task)

    def normalize(self, archive, logger):
        super().normalize(archive, logger)
        # TODO: When is_single_point_converged becomes an array, this should store
        # per-step convergence: [all(step_results) for step_results in single_point_convergence_results]
        # Currently aggregates across all steps into single boolean.
        single_point_convergence_results = jmespath.search(
            'workflow2.tasks[*].results.convergence[*].is_reached', archive
        )
        if single_point_convergence_results is None:
            return
        all_scf_converged = all(all(x) for x in single_point_convergence_results)
        self.results.is_single_point_converged = all_scf_converged


m_package.__init_metainfo__()
