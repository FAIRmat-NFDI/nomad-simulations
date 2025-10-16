from nomad.datamodel import EntryArchive
from nomad.metainfo import MEnum, Quantity
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .general import SerialWorkflow, SimulationWorkflowModel, SimulationWorkflowResults
from .thermodynamics import ThermodynamicsResults


class MolecularDynamicsModel(SimulationWorkflowModel):
    _label = 'MD parameters'

    thermodynamic_ensemble = Quantity(
        type=MEnum('NVE', 'NVT', 'NPT', 'NPH'),
        shape=[],
        description="""
        The type of thermodynamic ensemble that was simulated.

        Allowed values are:

        | Thermodynamic Ensemble          | Description                               |

        | ---------------------- | ----------------------------------------- |

        | `"NVE"`           | Constant number of particles, volume, and energy |

        | `"NVT"`           | Constant number of particles, volume, and temperature |

        | `"NPT"`           | Constant number of particles, pressure, and temperature |

        | `"NPH"`           | Constant number of particles, pressure, and enthalpy |
        """,
    )

    integrator_type = Quantity(
        type=MEnum(
            'brownian',
            'conjugant_gradient',
            'langevin_goga',
            'langevin_schneider',
            'leap_frog',
            'rRESPA_multitimescale',
            'velocity_verlet',
            'langevin_leap_frog',
        ),
        shape=[],
        description="""
        Name of the integrator.

        Allowed values are:

        | Integrator Name          | Description                               |

        | ---------------------- | ----------------------------------------- |

        | `"langevin_goga"`           | N. Goga, A. J. Rzepiela, A. H. de Vries,
        S. J. Marrink, and H. J. C. Berendsen, [J. Chem. Theory Comput. **8**, 3637 (2012)]
        (https://doi.org/10.1021/ct3000876) |

        | `"langevin_schneider"`           | T. Schneider and E. Stoll,
        [Phys. Rev. B **17**, 1302](https://doi.org/10.1103/PhysRevB.17.1302) |

        | `"leap_frog"`          | R.W. Hockney, S.P. Goel, and J. Eastwood,
        [J. Comp. Phys. **14**, 148 (1974)](https://doi.org/10.1016/0021-9991(74)90010-2) |

        | `"velocity_verlet"` | W.C. Swope, H.C. Andersen, P.H. Berens, and K.R. Wilson,
        [J. Chem. Phys. **76**, 637 (1982)](https://doi.org/10.1063/1.442716) |

        | `"rRESPA_multitimescale"` | M. Tuckerman, B. J. Berne, and G. J. Martyna
        [J. Chem. Phys. **97**, 1990 (1992)](https://doi.org/10.1063/1.463137) |

        | `"langevin_leap_frog"` | J.A. Izaguirre, C.R. Sweet, and V.S. Pande
        [Pac Symp Biocomput. **15**, 240-251 (2010)](https://doi.org/10.1142/9789814295291_0026) |
        """,
    )

    integration_timestep = Quantity(
        type=float,
        shape=[],
        unit='s',
        description="""
        The timestep at which the numerical integration is performed.
        """,
    )

    n_steps = Quantity(
        type=int,
        shape=[],
        description="""
        Number of timesteps performed.
        """,
    )

    coordinate_save_frequency = Quantity(
        type=int,
        shape=[],
        description="""
        The number of timesteps between saving the coordinates.
        """,
    )

    velocity_save_frequency = Quantity(
        type=int,
        shape=[],
        description="""
        The number of timesteps between saving the velocities.
        """,
    )

    force_save_frequency = Quantity(
        type=int,
        shape=[],
        description="""
        The number of timesteps between saving the forces.
        """,
    )

    thermodynamics_save_frequency = Quantity(
        type=int,
        shape=[],
        description="""
        The number of timesteps between saving the thermodynamic quantities.
        """,
    )


class MolecularDynamicsResults(ThermodynamicsResults):
    """
    Contains defintions for the results of a molecular dynamics calculation.
    """

    _label = 'MD results'


class MolecularDynamics(SerialWorkflow):
    _task_label = 'Step'

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = MolecularDynamicsModel()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = MolecularDynamicsResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)
