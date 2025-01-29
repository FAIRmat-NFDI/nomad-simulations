import numpy as np
from nomad.datamodel import EntryArchive
from nomad.metainfo import MEnum, Quantity, SchemaPackage
from structlog.stdlib import BoundLogger

from .general import (
    SimulationWorkflow,
    SimulationWorkflowModel,
    SimulationWorkflowResults,
)

m_package = SchemaPackage()


class GeometryOptimizationModel(SimulationWorkflowModel):
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

    convergence_tolerance_energy_difference = Quantity(
        type=float,
        shape=[],
        unit='joule',
        description="""
        The input energy difference tolerance criterion.
        """,
    )

    convergence_tolerance_force_maximum = Quantity(
        type=float,
        shape=[],
        unit='newton',
        description="""
        The input maximum net force tolerance criterion.
        """,
    )

    convergence_tolerance_stress_maximum = Quantity(
        type=float,
        shape=[],
        unit='pascal',
        description="""
        The input maximum stress tolerance criterion.
        """,
    )

    convergence_tolerance_displacement_maximum = Quantity(
        type=float,
        shape=[],
        unit='meter',
        description="""
        The input maximum displacement tolerance criterion.
        """,
    )

    optimization_steps_maximum = Quantity(
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


class GeometryOptimizationResults(SimulationWorkflowResults):
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
        shape=['optimization_steps'],
        description="""
        List of energy_total values gathered from the single configuration
        calculations that are a part of the optimization trajectory.
        """,
    )

    steps = Quantity(
        type=np.int32,
        shape=['optimization_steps'],
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

    is_converged_geometry = Quantity(
        type=bool,
        shape=[],
        description="""
        Indicates if the geometry convergence criteria were fulfilled.
        """,
    )


class GeometryOptimization(SimulationWorkflow):
    """
    Definitions for geometry optimization workflow.
    """

    task_label = 'Step'

    def generate_inputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.model:
            self.model = GeometryOptimizationModel()
        super().generate_inputs(archive, logger)

    def generate_outputs(self, archive: EntryArchive, logger: BoundLogger):
        if not self.results:
            self.results = GeometryOptimizationResults()
        super().generate_outputs(archive, logger)

    def generate_tasks(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().generate_tasks(archive, logger)
        for n, task in enumerate(self.tasks):
            if not task.name:
                task.name = f'{self.task_label} {n}'

        # link inputs to first task
        self.tasks[0].inputs.extend(self.inputs)
        # add outputs of last task to outputs
        self.outputs.extend(self.tasks[-1].outputs)


m_package.__init_metainfo__()
