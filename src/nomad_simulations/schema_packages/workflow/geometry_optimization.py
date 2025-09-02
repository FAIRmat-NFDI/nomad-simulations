import numpy as np
from nomad.datamodel import EntryArchive
from nomad.metainfo import MEnum, Quantity, SchemaPackage
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.properties.energies import BaseEnergy
from nomad_simulations.schema_packages.utils import log

from .general import SerialWorkflow, SimulationWorkflowModel, SimulationWorkflowResults

m_package = SchemaPackage()


class GeometryOptimizationModel(SimulationWorkflowModel):
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


class GeometryOptimizationResults(SimulationWorkflowResults):
    _label = 'Geometry optimiztation results'

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

    is_converged_geometry = Quantity(
        type=bool,
        shape=[],
        description="""
        Indicates if the geometry convergence criteria were fulfilled.
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


class GeometryOptimization(SerialWorkflow):
    """
    Definitions for geometry optimization workflow.
    """

    _task_label = 'Step'

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = GeometryOptimizationModel()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = GeometryOptimizationResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)


m_package.__init_metainfo__()
