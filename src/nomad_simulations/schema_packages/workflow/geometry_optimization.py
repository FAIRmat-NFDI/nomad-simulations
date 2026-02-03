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


class GeometryOptimizationMethod(SimulationWorkflowMethod):
    """
    Workflow model describing a geometry optimization.
    """

    _label = 'Geometry optimization parameters'

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

        | `"cell_volume"`         | `"atomic"` + cell lattice paramters are updated isotropically |

        | `"cell_shape"`        | `"cell_volume"` but without the isotropic constraint: all cell parameters are updated |

        """,
    )

    optimization_method = Quantity(
        type=str,
        shape=[],
        description="""
        The method used for geometry optimization. Some known possible values are:
        `"steepest_descent"`, `"conjugant_gradient"`, `"low_memory_broyden_fletcher_goldfarb_shanno"`.
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
        sub_section=WorkflowConvergenceTarget.m_def, repeats=True
    )


class GeometryOptimizationResults(SimulationWorkflowResults):
    _label = 'Geometry optimiztation results'

    is_single_point_converged = Quantity(
        type=bool,
        description="""
        Indicates if all single point SCF runs (if applicable) have converged to the
        specified target (true), or not (false).
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

        if not self.energies:
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
                denergies = energies[1:] - energies[: len(energies) - 1]
                self.final_energy_difference = (
                    denergies[denergies.nonzero()[0][-1]] * BaseEnergy.value.unit
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
        """
        # do not overwrite assigned tasks
        if self.tasks:
            return

        if not archive.data or not archive.data.outputs:
            return

        # do not overwrite if tasks are set but give out a warning that it maybe
        # inconsistent with the outputs
        logger = self.map_tasks.__annotations__['logger']
        if self.tasks:
            logger.warning('Tasks are predefined and will not generate from outputs.')
            return

        outputs = list(archive.data.outputs)
        outputs.sort(key=lambda x: x.wall_start or 0)
        tasks = []
        parent_n = 0
        root_n = 0
        for n, output in enumerate(outputs):
            if output.get('scf_steps') is not None:
                task = SinglePoint(
                    name=f'{self._task_label} {n}',
                    outputs=[Link(name='Outputs', section=output)],
                    results=SimulationWorkflowResults(),
                )
                single_point_convergence = jmespath.search(
                    'workflow2.method.single_point_convergence_targets', archive
                )
                if single_point_convergence is not None:
                    single_point_convergence_result = task._resolve_convergence(
                        archive, single_point_convergence, logger
                    )
                    task.results.convergence_targets = single_point_convergence_result
            else:
                task = Task(
                    name=f'{self._task_label} {n}',
                    outputs=[Link(name='Outputs', section=output)],
                )
            tasks.append(task)
            tstart = output.wall_start
            tend = outputs[parent_n].wall_end
            if tstart is None and tend is None:
                continue
            if tstart >= tend:
                task.inputs.extend(
                    [Link(name='Linked task', section=t) for t in tasks[parent_n:n]]
                )
                root_n = parent_n
                parent_n = n
            elif n != parent_n:
                task.inputs.extend(
                    [
                        Link(name='Linked task', section=t)
                        for t in tasks[root_n:parent_n]
                    ]
                )

        self.tasks.extend(tasks)

    def normalize(self, archive, logger):
        super().normalize(archive, logger)
        single_point_convergence_results = jmespath.search(
            'workflow2.tasks[*].results.convergence_targets[*].is_reached', archive
        )
        if single_point_convergence_results is None:
            return
        all_scf_converged = all(all(x) for x in single_point_convergence_results)
        self.results.is_single_point_converged = all_scf_converged


m_package.__init_metainfo__()
