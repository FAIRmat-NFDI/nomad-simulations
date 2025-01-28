from nomad.datamodel import EntryArchive
from nomad.datamodel.metainfo.workflow import Link, Task
from nomad.metainfo import MEnum, Quantity
from nomad.metainfo.util import MSubSectionList
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.outputs import Outputs

from .general import (
    SimulationWorkflow,
    SimulationWorkflowMethod,
    SimulationWorkflowResults,
)


class GeometryOptimizationMethod(SimulationWorkflowMethod):
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
        The number of optimization steps between sucessive outputs.
        """,
    )


class GeometryOptimizationResults(SimulationWorkflowResults):
    pass


class GeometryOptimization(SimulationWorkflow):
    """
    Definitions for geometry optimization workflow.
    """

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Specify the inputs and outputs of the tasks as the model system.
        """

        # set up first method and results before we call base normalizer
        if not self.method:
            self.method = GeometryOptimizationMethod()

        if not self.results:
            self.results = GeometryOptimizationResults()

        super().normalize(archive, logger)

        def extend_links(task: Task) -> None:
            def get_system_links(links: MSubSectionList, name: str) -> list[Link]:
                return [
                    Link(name=name, section=link.section.model_system_ref)
                    for link in links
                    if isinstance(link.section, Outputs)
                    and link.section.model_system_ref
                ]

            task.inputs.extend(get_system_links(self.inputs, 'Input system'))
            task.outputs.extend(get_system_links(self.outputs, 'Output system'))

        if not self.name:
            self.name = 'Geometry Optimization'

        extend_links(self)
        for n, task in enumerate(self.tasks):
            if not task.name:
                task.name = f'Step {n}'
            extend_links(task)
