from __future__ import annotations

from array import array
from collections import namedtuple
from itertools import chain
from typing import TYPE_CHECKING, Any

import networkx
import numpy as np
from scipy import sparse
from scipy.stats import linregress

try:
    import MDAnalysis

    _HAS_MDA = True
except ImportError:
    _HAS_MDA = False

if TYPE_CHECKING:
    from MDAnalysis.core.universe import Universe

from nomad import atomutils
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.hdf5 import HDF5Dataset
from nomad.datamodel.metainfo.workflow import Link
from nomad.metainfo import MEnum, MSection, Quantity, Reference, Section, SubSection
from nomad.units import ureg

from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.numerical_settings import NumericalSettings
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties.structure import RadiusOfGyration
from nomad_simulations.schema_packages.utils import log
from nomad_simulations.schema_packages.utils.molecular_dynamics import (
    BeadGroup,
    _get_molecular_bead_groups,
    archive_to_universe,
    calc_molecular_msd,
    calc_molecular_rdf,
    calc_molecular_rg,
)
from nomad_simulations.schema_packages.workflow.trajectory import RadiiOfGyration

from .general import (
    SerialWorkflow,
    SerialWorkflowResults,
    SimulationWorkflowMethod,
    SimulationWorkflowResults,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    import pint
    from nomad.datamodel.context import Context
    from nomad.metainfo import Section
    from structlog.stdlib import BoundLogger


class MDSettings(NumericalSettings):
    """
    Abstract class for classifying numerical settings relevant for molecular dynamics runs.
    """

    frame_start = Quantity(
        type=int,
        shape=[],
        description="""
        Trajectory frame number where the application of these settings start.
        """,
    )

    frame_end = Quantity(
        type=int,
        shape=[],
        description="""
        Trajectory frame number where the application of these settings end.
        """,
    )


class ThermostatParameters(MDSettings):
    """
    Section containing the parameters pertaining to the thermostat for a molecular dynamics run.
    """

    thermostat_type = Quantity(
        type=MEnum(
            'andersen',
            'berendsen',
            'brownian',
            'dissipative_particle_dynamics',
            'langevin_goga',
            'langevin_leap_frog',
            'langevin_schneider',
            'nose_hoover',
            'velocity_rescaling',
            'velocity_rescaling_langevin',
            'velocity_rescaling_woodcock',
        ),
        shape=[],
        description="""
        The name of the thermostat used for temperature control. If skipped or an empty string is used, it
        means no thermostat was applied.

        Allowed values are:

        | Thermostat Name        | Description                               |

        | ---------------------- | ----------------------------------------- |

        | `""`                   | No thermostat               |

        | `"andersen"`           | H.C. Andersen, [J. Chem. Phys.
        **72**, 2384 (1980)](https://doi.org/10.1063/1.439486) |

        | `"berendsen"`          | H. J. C. Berendsen, J. P. M. Postma,
        W. F. van Gunsteren, A. DiNola, and J. R. Haak, [J. Chem. Phys.
        **81**, 3684 (1984)](https://doi.org/10.1063/1.448118) |

        | `"brownian"`           | Brownian Dynamics |

        | `"dissipative_particle_dynamics"` | R.D. Groot and P.B. Warren
        [J. Chem. Phys. **107**(11), 4423-4435 (1997)](https://doi.org/10.1063/1.474784) |

        | `"langevin_goga"`           | N. Goga, A. J. Rzepiela, A. H. de Vries,
        S. J. Marrink, and H. J. C. Berendsen, [J. Chem. Theory Comput. **8**, 3637 (2012)]
        (https://doi.org/10.1021/ct3000876) |

        | `"langevin_leap_frog"` | J.A. Izaguirre, C.R. Sweet, and V.S. Pande
        [Pac Symp Biocomput. **15**, 240-251 (2010)](https://doi.org/10.1142/9789814295291_0026) |

        | `"langevin_schneider"`           | T. Schneider and E. Stoll,
        [Phys. Rev. B **17**, 1302](https://doi.org/10.1103/PhysRevB.17.1302) |

        | `"nose_hoover"`        | S. Nosé, [Mol. Phys. **52**, 255 (1984)]
        (https://doi.org/10.1080/00268978400101201); W.G. Hoover, [Phys. Rev. A
        **31**, 1695 (1985) |

        | `"velocity_rescaling"` | G. Bussi, D. Donadio, and M. Parrinello,
        [J. Chem. Phys. **126**, 014101 (2007)](https://doi.org/10.1063/1.2408420) |

        | `"velocity_rescaling_langevin"` | G. Bussi and M. Parrinello,
        [Phys. Rev. E **75**, 056707 (2007)](https://doi.org/10.1103/PhysRevE.75.056707) |

        | `"velocity_rescaling_woodcock"` | L. V. Woodcock,
        [Chem. Phys. Lett. **10**, 257 (1971)](https://doi.org/10.1016/0009-2614(71)80281-6) |
        """,
    )

    reference_temperature = Quantity(
        type=np.float64,
        shape=[],
        unit='kelvin',
        description="""
        The target temperature for the simulation. Typically used when temperature_profile is "constant".
        """,
    )

    coupling_constant = Quantity(
        type=np.float64,
        shape=[],
        unit='s',
        description="""
        The time constant for temperature coupling. Need to describe what this means for the various
        thermostat options...
        """,
    )

    effective_mass = Quantity(
        type=np.float64,
        shape=[],
        unit='kilogram',
        description="""
        The effective or fictitious mass of the temperature resevoir.
        """,
    )

    temperature_profile = Quantity(
        type=MEnum('constant', 'linear', 'exponential'),
        shape=[],
        description="""
        Type of temperature control (i.e., annealing) procedure. Can be "constant" (no annealing), "linear", or "exponential".
        If linear, "temperature_update_delta" specifies the corresponding update parameter.
        If exponential, "temperature_update_factor" specifies the corresponding update parameter.
        """,
    )

    reference_temperature_start = Quantity(
        type=np.float64,
        shape=[],
        unit='kelvin',
        description="""
        The initial target temperature for the simulation. Typically used when temperature_profile is "linear" or "exponential".
        """,
    )

    reference_temperature_end = Quantity(
        type=np.float64,
        shape=[],
        unit='kelvin',
        description="""
        The final target temperature for the simulation.  Typically used when temperature_profile is "linear" or "exponential".
        """,
    )

    temperature_update_frequency = Quantity(
        type=int,
        shape=[],
        description="""
        Number of simulation steps between changing the target temperature.
        """,
    )

    temperature_update_delta = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Amount to be added (subtracted if negative) to the current reference_temperature
        at a frequency of temperature_update_frequency when temperature_profile is "linear".
        The reference temperature is then replaced by this new value until the next update.
        """,
    )

    temperature_update_factor = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Factor to be multiplied to the current reference_temperature at a frequency of temperature_update_frequency when temperature_profile is exponential.
        The reference temperature is then replaced by this new value until the next update.
        """,
    )

    step_start = Quantity(
        type=int,
        shape=[],
        description="""
        Trajectory step where this thermostating starts.
        """,
    )

    step_end = Quantity(
        type=int,
        shape=[],
        description="""
        Trajectory step number where this thermostating ends.
        """,
    )


class BarostatParameters(MDSettings):
    """
    Section containing the parameters pertaining to the barostat for a molecular dynamics run.
    """

    m_def = Section(validate=False)

    barostat_type = Quantity(
        type=MEnum(
            'berendsen',
            'martyna_tuckerman_tobias_klein',
            'nose_hoover',
            'parrinello_rahman',
            'stochastic_cell_rescaling',
        ),
        shape=[],
        description="""
        The name of the barostat used for temperature control. If skipped or an empty string is used, it
        means no barostat was applied.

        Allowed values are:

        | Barostat Name          | Description                               |

        | ---------------------- | ----------------------------------------- |

        | `""`                   | No thermostat               |

        | `"berendsen"`          | H. J. C. Berendsen, J. P. M. Postma,
        W. F. van Gunsteren, A. DiNola, and J. R. Haak, [J. Chem. Phys.
        **81**, 3684 (1984)](https://doi.org/10.1063/1.448118) |

        | `"martyna_tuckerman_tobias_klein"` | G.J. Martyna, M.E. Tuckerman, D.J. Tobias, and M.L. Klein,
        [Mol. Phys. **87**, 1117 (1996)](https://doi.org/10.1080/00268979600100761);
        M.E. Tuckerman, J. Alejandre, R. López-Rendón, A.L. Jochim, and G.J. Martyna,
        [J. Phys. A. **59**, 5629 (2006)](https://doi.org/10.1088/0305-4470/39/19/S18)|

        | `"nose_hoover"`        | S. Nosé, [Mol. Phys. **52**, 255 (1984)]
        (https://doi.org/10.1080/00268978400101201); W.G. Hoover, [Phys. Rev. A
        **31**, 1695 (1985) |

        | `"parrinello_rahman"`        | M. Parrinello and A. Rahman,
        [J. Appl. Phys. **52**, 7182 (1981)](https://doi.org/10.1063/1.328693);
        S. Nosé and M.L. Klein, [Mol. Phys. **50**, 1055 (1983) |

        | `"stochastic_cell_rescaling"` | M. Bernetti and G. Bussi,
        [J. Chem. Phys. **153**, 114107 (2020)](https://doi.org/10.1063/1.2408420) |
        """,
    )

    coupling_type = Quantity(
        type=MEnum('isotropic', 'semi_isotropic', 'anisotropic'),
        shape=[],
        description="""
        Describes the symmetry of pressure coupling. Specifics can be inferred from the `coupling constant`

        | Type          | Description                               |

        | ---------------------- | ----------------------------------------- |

        | `isotropic`          | Identical coupling in all directions. |

        | `semi_isotropic` | Identical coupling in 2 directions. |

        | `anisotropic`        | General case. |
        """,
    )

    reference_pressure = Quantity(
        type=np.float64,
        shape=[3, 3],
        unit='pascal',
        description="""
        The target pressure for the simulation, stored in a 3x3 matrix, indicating the values for individual directions
        along the diagonal, and coupling between directions on the off-diagonal. Typically used when pressure_profile is "constant".
        """,
    )

    coupling_constant = Quantity(
        type=np.float64,
        shape=[3, 3],
        unit='s',
        description="""
        The time constants for pressure coupling, stored in a 3x3 matrix, indicating the values for individual directions
        along the diagonal, and coupling between directions on the off-diagonal. 0 values along the off-diagonal
        indicate no-coupling between these directions.
        """,
    )

    compressibility = Quantity(
        type=np.float64,
        shape=[3, 3],
        unit='1 / pascal',
        description="""
        An estimate of the system's compressibility, used for box rescaling, stored in a 3x3 matrix indicating the values for individual directions
        along the diagonal, and coupling between directions on the off-diagonal. If None, it may indicate that these values
        are incorporated into the coupling_constant, or simply that the software used uses a fixed value that is not available in
        the input/output files.
        """,
    )

    pressure_profile = Quantity(
        type=MEnum('constant', 'linear', 'exponential'),
        shape=[],
        description="""
        Type of pressure control procedure. Can be "constant" (no annealing), "linear", or "exponential".
        If linear, "pressure_update_delta" specifies the corresponding update parameter.
        If exponential, "pressure_update_factor" specifies the corresponding update parameter.
        """,
    )

    reference_pressure_start = Quantity(
        type=np.float64,
        shape=[3, 3],
        unit='pascal',
        description="""
        The initial target pressure for the simulation, stored in a 3x3 matrix, indicating the values for individual directions
        along the diagonal, and coupling between directions on the off-diagonal. Typically used when pressure_profile is "linear" or "exponential".
        """,
    )

    reference_pressure_end = Quantity(
        type=np.float64,
        shape=[3, 3],
        unit='pascal',
        description="""
        The final target pressure for the simulation, stored in a 3x3 matrix, indicating the values for individual directions
        along the diagonal, and coupling between directions on the off-diagonal.  Typically used when pressure_profile is "linear" or "exponential".
        """,
    )

    pressure_update_frequency = Quantity(
        type=int,
        shape=[],
        description="""
        Number of simulation steps between changing the target pressure.
        """,
    )

    pressure_update_delta = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Amount to be added (subtracted if negative) to the current reference_pressure
        at a frequency of pressure_update_frequency when pressure_profile is "linear".
        The pressure temperature is then replaced by this new value until the next update.
        """,
    )

    pressure_update_factor = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Factor to be multiplied to the current reference_pressure at a frequency of pressure_update_frequency when pressure_profile is exponential.
        The reference pressure is then replaced by this new value until the next update.
        """,
    )

    step_start = Quantity(
        type=int,
        shape=[],
        description="""
        Trajectory step where this barostating starts.
        """,
    )

    step_end = Quantity(
        type=int,
        shape=[],
        description="""
        Trajectory step number where this barostating ends.
        """,
    )


class ShearParameters(MDSettings):
    """
    Section containing the parameters pertaining to the shear flow for a molecular dynamics run.
    """

    m_def = Section(validate=False)

    shear_type = Quantity(
        type=MEnum('lees_edwards', 'trozzi_ciccotti', 'ashurst_hoover'),
        shape=[],
        description="""
        The name of the method used to implement the effect of shear flow within the simulation.

        Allowed values are:

        | Shear Method          | Description                               |

        | ---------------------- | ----------------------------------------- |

        | `""`                   | No thermostat               |

        | `"lees_edwards"`          | A.W. Lees and S.F. Edwards,
        [J. Phys. C **5** (1972) 1921](https://doi.org/10.1088/0022-3719/5/15/006)|

        | `"trozzi_ciccotti"`          | A.W. Lees and S.F. Edwards,
        [Phys. Rev. A **29** (1984) 916](https://doi.org/10.1103/PhysRevA.29.916)|

        | `"ashurst_hoover"`          | W. T. Ashurst and W. G. Hoover,
        [Phys. Rev. A **11** (1975) 658](https://doi.org/10.1103/PhysRevA.11.658)|
        """,
    )

    shear_rate = Quantity(
        type=np.float64,
        shape=[3, 3],
        unit='ps^-1',
        description="""
        The external stress tensor include normal (diagonal elements; which are zero in shear simulations)
        and shear stress' rates (off-diagonal elements).
        Its elements are: [[σ_x, τ_yx, τ_zx], [τ_xy, σ_y, τ_zy], [τ_xz, τ_yz, σ_z]],
		where σ and τ are the normal and shear stress' rates.
        The first and second letters in the index correspond to the normal vector to the shear plane and the direction of shearing, respectively.
        """,
    )

    step_start = Quantity(
        type=int,
        shape=[],
        description="""
        Trajectory step where this shearing starts.
        """,
    )

    step_end = Quantity(
        type=int,
        shape=[],
        description="""
        Trajectory step number where this shearing ends.
        """,
    )


class Lambdas(ArchiveSection):
    """
    Parameters for one lambda dimension / interaction type.
    """

    m_def = Section(validate=False)

    interaction_type = Quantity(
        type=MEnum(
            'output', 'coulomb', 'vdw', 'bonded', 'restraint', 'mass', 'temperature'
        ),
        shape=[],
        description="""
        The type of lambda interpolation

        Allowed values are:

        | type          | Description                               |

        | ---------------------- | ----------------------------------------- |

        | `"output"`           | Lambdas for the free energy outputs saved.
                                    These will also act as a default in case some
                                    relevant lambdas are not specified. |

        | `"coulomb"`          | Lambdas for interpolating electrostatic interactions. |

        | `"vdw"`              | Lambdas for interpolating van der Waals interactions. |

        | `"bonded"`           | Lambdas for interpolating all intramolecular interactions. |

        | `"restraint"`        | Lambdas for interpolating restraints. |

        | `"mass"`             | Lambdas for interpolating masses. |

        | `"temperature"`      | Lambdas for interpolating temperature. |
        """,
    )

    values = Quantity(
        type=np.float64,
        shape=['*'],
        description='Grid of λ values for this interaction (e.g., [0.0, 0.1, …, 1.0]).',
    )

    # Explicit endpoint states live WITH the schedule they qualify
    endpoints_on = Quantity(
        type=bool,
        shape=[2],
        description='Specifies whether the interaction is ‘on’ at the endpoints: [initial@λ=0, final@λ=1].',
    )

    # Optional alchemical details often needed for reproducibility
    # TODO these should be re-evaluated in the context of real test data / in communication with experts
    scheme = Quantity(
        type=MEnum('decouple', 'annihilate'),
        shape=[],
        description='Alchemical scheme for this interaction, if applicable.',
    )

    softcore_enabled = Quantity(
        type=bool, shape=[], description='Soft-core on/off for nonbonded.'
    )

    softcore_alpha = Quantity(
        type=np.float64,
        shape=[],
        description='Soft-core α parameter.',
    )

    softcore_p = Quantity(
        type=np.int32,
        shape=[],
        description='Soft-core power p.',
    )

    softcore_sigma = Quantity(
        type=np.float64,
        shape=[],
        description='Soft-core σ (if used).',
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        # Basic λ-grid validation
        vals = self.values or []
        if len(vals) == 0:
            logger.warning(
                'No Lambda grid is defined; downstream behavior may be undefined.'
            )
        else:
            # monotonic non-decreasing check
            if any(vals[i] > vals[i + 1] for i in range(len(vals) - 1)):
                logger.warning(
                    'Lambda grid is not monotonic non-decreasing; results may be inconsistent.'
                )

        # Scheme applicability (only meaningful for nonbonded)
        is_nonbonded = self.interaction_type in ('vdw', 'coulomb')
        if not is_nonbonded:
            if (
                self.scheme is not None
                or self.softcore_enabled is not None
                or self.softcore_alpha is not None
                or self.softcore_p is not None
                or self.softcore_sigma is not None
            ):
                logger.warning(
                    'An alchemical scheme and/or corresponding parameters are set for a non-nonbonded interaction, '
                    'but these are only applicable to nonbonded interactions.'
                )

        # Soft-core applicability and parameter sanity
        if self.softcore_enabled:
            if self.softcore_alpha is None:
                logger.info('Soft-core is enabled without a defined alpha.')
            if self.softcore_p is not None and self.softcore_p < 0:
                logger.warning('Soft-core exponent is negative.')
            # softcore_sigma can be optional; add a gentle hint if unset
            if self.softcore_sigma is None:
                logger.info('Soft-core is enabled without a defined sigma.')


class FreeEnergyCalculationParameters(MDSettings):
    """
    Parameters for a free energy workflow run.
    """

    m_def = Section(validate=False)

    calc_type = Quantity(
        type=MEnum('alchemical', 'umbrella_sampling'),
        shape=[],
        description="""
        Specifies the type of workflow. Allowed values are:

        | kind          | Description                               |

        | ---------------------- | ----------------------------------------- |

        | `"alchemical"`           | A non-physical transformation between 2 well-defined systems,
                                     typically achieved by smoothly interpolating between Hamiltonians or force fields.  |

        | `"umbrella_sampling"`    | A sampling of the path between 2 well-defined (sub)states of a system,
                                     typically achieved by applying a biasing force to the force field along a
                                     specified reaction coordinate.
        """,
    )

    lambdas = SubSection(
        sub_section=Lambdas.m_def,
        description='Per-interaction lambda schedules and endpoint semantics.',
        repeats=True,
    )

    # If your runs share one aligned λ grid across all targets, keep a single index:
    # TODO check if we make this a helper variable only for the normalization
    current_lambda_index = Quantity(
        type=int,
        shape=[],
        description='Index of each Lambdas.values for the current simulation step/state '
        '(only valid if all targets share an aligned λ grid).',
    )
    # Otherwise, prefer per-target scalar λ values for the current state (one scalar per Lambdas entry):
    current_lambdas = Quantity(
        type=np.float64, shape=['*'], description='Scalar λ per Lambdas entry order.'
    )
    # TODO not really sure how to deal with this, cause it corresponds to a hierarchical workflow that may not be contained in the same upload

    # TODO make sure this is covered in the outputs
    # atom_indices = Quantity(
    #     type=np.dtype(np.int32),
    #     shape=['*'],
    #     description='Particle indices involved in the interpolation/selection.',
    # )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        # Collapse multiple "output" entries: keep the first, drop the rest
        output_idxs = [
            i for i, lam in enumerate(self.lambdas) if lam.interaction_type == 'output'
        ]
        if len(output_idxs) > 1:
            logger.warning(
                'Multiple "output" Lambda entries detected; only the first one will be kept.'
            )
            for i in sorted(output_idxs[1:], reverse=True):
                del self.lambdas[i]

        # Check uniqueness of interaction_type (non-"output")
        interaction_types = [
            lam.interaction_type
            for lam in self.lambdas
            if lam.interaction_type is not None and lam.interaction_type != 'output'
        ]
        if len(interaction_types) != len(set(interaction_types)):
            logger.warning(
                'Duplicate Lambda interaction types detected; duplicates may indicate inconsistent setup.'
            )

        # Range checks for λ grids (alchemical: expect [0,1] for common targets)
        strict_targets = {'vdw', 'coulomb', 'bonded', 'mass'}
        if self.calc_type == 'alchemical':
            values = np.array(
                [
                    val
                    for lam in self.lambdas
                    if lam.interaction_type in strict_targets and lam.values
                    for val in lam.values
                ]
            )
            if values.size > 0 and (np.any(values < 0.0) or np.any(values > 1.0)):
                logger.warning(
                    'One or more Lambda grids for alchemical targets are outside the expected [0,1] range.'
                )

        # Alignment check for single current_lambda_index
        if self.current_lambda_index is not None:
            grids = [tuple(getattr(lam, 'values', []) or []) for lam in self.lambdas]
            non_empty = [g for g in grids if len(g) > 0]
            if len(non_empty) > 1 and any(g != non_empty[0] for g in non_empty[1:]):
                logger.warning(
                    'A single current_lambda_index was provided but Lambda grids differ; index will be ignored.'
                )
                self.current_lambda_index = None
            else:
                grid_len = len(non_empty[0]) if non_empty else 0
                if grid_len == 0:
                    logger.warning(
                        'A current_lambda_index was provided but no Lambda grid is defined; index will be cleared.'
                    )
                    self.current_lambda_index = None
                elif not (0 <= self.current_lambda_index < grid_len):
                    logger.warning(
                        'The current_lambda_index is out of bounds and will be adjusted to a valid range.'
                    )
                    self.current_lambda_index = max(
                        0, min(self.current_lambda_index, grid_len - 1)
                    )

        # Validate per-target scalar λs if present
        current_lambdas = self.current_lambdas
        if current_lambdas is not None:
            n_targets = len(self.lambdas)
            if len(current_lambdas) != n_targets:
                logger.warning(
                    'The number of current Lambda values does not match the number of Lambda entries.'
                )
            if self.calc_type == 'alchemical' and any(
                not (0.0 <= lam_val <= 1.0) for lam_val in current_lambdas
            ):
                logger.warning(
                    'One or more current Lambda values are outside the expected [0,1] range.'
                )

        # Use single "output" grid as default for missing per-target grids
        output_grid = None
        for lam in self.lambdas:
            if lam.interaction_type == 'output' and lam.values:
                output_grid = list(lam.values)
                break
        if output_grid is not None:
            for lam in self.lambdas:
                if lam.interaction_type != 'output':
                    vals = lam.values
                    if vals is None or len(vals) == 0:
                        lam.values = list(output_grid)
                        logger.info(
                            'Missing Lambda grids have been filled from the "output" grid.'
                        )


class MolecularDynamicsMethod(SimulationWorkflowMethod):
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
        type=np.float64,
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

    thermostat_parameters = SubSection(
        sub_section=ThermostatParameters.m_def, repeats=True
    )

    barostat_parameters = SubSection(sub_section=BarostatParameters.m_def, repeats=True)

    shear_parameters = SubSection(sub_section=ShearParameters.m_def, repeats=True)

    free_energy_calculation_parameters = SubSection(
        sub_section=FreeEnergyCalculationParameters.m_def, repeats=True
    )


class EnsembleProperty(PhysicalProperty):
    """
    Abstract base section for static observables calculated from a trajectory (i.e., from an ensemble average).
    This is an abstract class not intended to be directly populated. Use concrete implementations instead.
    """

    n_smooth = Quantity(
        type=int,
        shape=[],
        description="""
        Number of bins over which the running average was computed for
        the observable `values'.
        """,
    )

    n_prune = Quantity(
        type=int,
        shape=[],
        description="""
        Frequency with which to select frames for calculation of the observable `values'.
        """,
    )

    n_variables = Quantity(
        type=int,
        shape=[],
        description="""
        Number of variables along which the property is determined.
        """,
    )

    variables_name = Quantity(
        type=str,
        shape=['n_variables'],
        description="""
        Name/description of the independent variables along which the observable is defined.
        """,
    )

    n_bins = Quantity(
        type=int,
        shape=[],
        description="""
        Number of bins.
        """,
    )

    bins: Quantity = None

    frame_start = Quantity(
        type=int,
        shape=[],
        description="""
        Trajectory frame number where the ensemble averaging starts.
        """,
    )

    frame_end = Quantity(
        type=int,
        shape=[],
        description="""
        Trajectory frame number where the ensemble averaging ends.
        """,
    )


class RadialDistributionFunction(EnsembleProperty):
    """
    Section containing information about the calculation of
    radial distribution functions (rdfs).
    """

    _rdf_results: dict[str, Any] | None = None

    bins = Quantity(
        type=np.float64,
        shape=['n_bins'],
        unit='m',
        description="""
        Distances along which the rdf was calculated.
        """,
    )

    value = Quantity(
        type=np.float64,
        shape=['n_bins'],
        description="""
        Values of the property.
        """,
    )


class DiffusionConstant(EnsembleProperty):
    """
    Section containing information regarding the diffusion constants.
    """

    m_def = Section(validate=False)

    value = Quantity(
        type=np.float64,
        shape=[],
        unit='m^2/s',
        description="""
        Values of the diffusion constants.
        """,
    )


class CorrelationFunction(PhysicalProperty):
    """
    Abstract base section for time correlation functions calculated from a trajectory.
    This is an abstract class not intended to be directly populated. Use concrete implementations instead.
    """

    direction = Quantity(
        type=MEnum('x', 'y', 'z', 'xy', 'yz', 'xz', 'xyz'),
        shape=[],
        description="""
        Describes the direction in which the correlation function was calculated.
        """,
    )

    n_times = Quantity(
        type=int,
        shape=[],
        description="""
        Number of times windows for the calculation of the correlation function.
        """,
    )

    times = Quantity(
        type=np.float64,
        shape=['n_times'],
        unit='s',
        description="""
        Time windows used for the calculation of the correlation function.
        """,
    )


class MeanSquaredDisplacement(CorrelationFunction):
    """
    Section containing information about a calculation of any mean squared displacements (msds).
    """

    _msd_results: dict[str, Any] | None = None

    value = Quantity(
        type=np.float64,
        shape=['n_times'],
        unit='m^2',
        description="""
        Mean squared displacement values.
        """,
    )


class MolecularDynamicsResults(SerialWorkflowResults):
    _label = 'MD results'
    _cache: dict[str, Any] = {}
    _universe: Universe | None = None
    _bead_groups: dict[str, BeadGroup] | None = None

    n_steps = Quantity(
        type=np.int32,
        shape=[],
        description="""
        Number of trajectory steps""",
    )

    trajectory = Quantity(
        type=Reference(ModelSystem),
        shape=['n_steps'],
        description="""
        Reference to the system of each step in the trajectory.
        """,
    )

    # Properties
    diffusion_constants = SubSection(sub_section=DiffusionConstant.m_def, repeats=True)

    mean_squared_displacements = SubSection(
        sub_section=MeanSquaredDisplacement.m_def, repeats=True
    )

    radial_distribution_functions = SubSection(
        sub_section=RadialDistributionFunction.m_def, repeats=True
    )

    @log
    def get_universe(self, archive) -> Universe | None:
        logger = self.get_universe.__annotations__['logger']
        if self._universe:
            return self._universe
        if not _HAS_MDA:
            logger.warning(
                'MDAnalysis is not installed. Skipping MD results normalization. '
                'Install with `pip install nomad-simulations[md]`.'
            )
            return None
        try:
            universe = archive_to_universe(archive)
        except Exception:
            universe = None
            logger.warning(
                'Could not convert archive to MDAnalysis Universe, skipping MD results normalization.'
            )
        return universe

    @log
    def _get_molecular_rdfs(
        self, archive: EntryArchive
    ) -> list[RadialDistributionFunction]:
        # logger = self._get_molecular_rdfs.__annotations__['logger']
        if not self.radial_distribution_functions:
            return self.radial_distribution_functions

        n_traj_split = 10  # number of intervals to split trajectory into for averaging
        try:
            n_prune = int(
                self._universe.trajectory.n_frames / len(archive.data.model_system)
            )
        except Exception:
            n_prune = 1

        interval_indices: list[
            np.ndarray
        ] = []  # 2D array specifying the groups of the n_traj_split intervals to be averaged
        # first 20% of trajectory
        interval_indices.append(np.arange(int(n_traj_split * 0.20)))
        # last 80% of trajectory
        interval_indices.append(np.arange(n_traj_split)[len(interval_indices[0]) :])
        # last 60% of trajectory
        interval_indices.append(np.arange(n_traj_split)[len(interval_indices[0]) * 2 :])
        # last 40% of trajectory
        interval_indices.append(np.arange(n_traj_split)[len(interval_indices[0]) * 3 :])

        rdf_results = calc_molecular_rdf(
            self._universe,
            self._bead_groups,
            n_traj_split=n_traj_split,
            n_prune=n_prune,
            interval_indices=interval_indices,
        )
        sec_rdfs = []
        if rdf_results:
            for i_pair, pair_type in enumerate(rdf_results.get('types', [])):
                rdf = RadialDistributionFunction()
                rdf.type = rdf_results.get(
                    'type'
                )  # TODO this no longer exists (atomic, molecular)
                rdf.n_smooth = rdf_results.get('n_smooth')
                rdf.n_prune = n_prune
                rdf.n_variables = 1
                rdf.variables_name = ['distance']

                rdf.label = str(pair_type)
                bins_list = rdf_results.get('bins', [])
                value_list = rdf_results.get('value', [])
                frame_start_list = rdf_results.get('frame_start', [])
                frame_end_list = rdf_results.get('frame_end', [])

                rdf.n_bins = len(bins_list[i_pair]) if i_pair < len(bins_list) else 0
                rdf.bins = (
                    bins_list[i_pair] if i_pair < len(bins_list) else np.array([])
                )
                rdf.value = (
                    value_list[i_pair] if i_pair < len(value_list) else np.array([])
                )
                rdf.frame_start = (
                    frame_start_list[i_pair] if i_pair < len(frame_start_list) else 0
                )
                rdf.frame_end = (
                    frame_end_list[i_pair] if i_pair < len(frame_end_list) else 0
                )
                sec_rdfs.append(rdf)

        return sec_rdfs

    @log
    def _get_molecular_msds(
        self,
    ) -> tuple[list[MeanSquaredDisplacement], list[DiffusionConstant]]:
        # logger = self._get_molecular_msds.__annotations__['logger']
        if (
            self.mean_squared_displacements is not None
        ):  # TODO add check for diffusion_constants too?
            return self.mean_squared_displacements, self.diffusion_constants or []

        msd_results = calc_molecular_msd(self._universe, self._bead_groups)
        sec_msds: list[MeanSquaredDisplacement] = []
        sec_diffusion_constants: list[DiffusionConstant] = []
        if msd_results:
            for i_type, moltype in enumerate(msd_results.get('types', [])):
                msd = MeanSquaredDisplacement()
                msd.type = msd_results.get('type')
                msd.direction = msd_results.get('direction')
                msd.label = str(moltype)
                msd.n_times = len(msd_results.get('times', [[]] * i_type)[i_type])
                msd.times = (
                    msd_results['times'][i_type]
                    if msd_results.get('times') is not None
                    else []
                )
                msd.value = (
                    msd_results['value'][i_type]
                    if msd_results.get('value') is not None
                    else []
                )
                diffusion_constant = DiffusionConstant()
                diffusion_constant.value = (
                    msd_results['diffusion_constant'][i_type]
                    if msd_results.get('diffusion_constant') is not None
                    else []
                )
                if diffusion_constant.value is not None:
                    diffusion_constant.error_type = (
                        'Pearson correlation coefficient'  # TODO Update treatment!
                    )
                    if msd_results.get('error_diffusion_constant') is not None:
                        errors = msd_results['error_diffusion_constant'][i_type]
                        diffusion_constant.errors = (
                            list(errors)
                            if isinstance(errors, list | np.ndarray)
                            else [errors]
                        )
                    diffusion_constant.is_derived = True
                    diffusion_constant.physical_property_ref = [msd]
                    sec_diffusion_constants.append(diffusion_constant)
                sec_msds.append(msd)

        return sec_msds, sec_diffusion_constants

    def _populate_output_rgs(
        self, archive: EntryArchive, rg_results: list, logger
    ) -> None:
        """
        Populate the radius of gyration data in the archive's output sections.
        This is separated from the workflow calculation to maintain clean separation of concerns.
        """
        try:
            data = archive.data
            sec_systems = data.system
            sec_outputs = data.outputs
        except Exception:
            logger.warning('Could not access archive data for populating output RGs')
            return

        for rg in rg_results:
            n_frames = rg.get('n_frames')
            if len(sec_systems) != n_frames:
                logger.warning(
                    'Mismatch in length of system references in calculation and calculated Rg values. '
                    'Will not store Rg values under calculation section'
                )
                continue

            for out in sec_outputs:
                if not out.model_system_ref:  # TODO check relevance
                    continue
                sys_ind = out.model_system_ref.m_parent_index

                # Use the correct property name from outputs.py (radii_of_gyration, plural)
                if not hasattr(out, 'radii_of_gyration') or not out.radii_of_gyration:
                    sec_rgs_out = out.m_create(RadiusOfGyration)
                    sec_rgs_out.kind = rg.get('type')  # check quant names
                else:
                    sec_rgs_out = out.radii_of_gyration[0]

                # TODO Fix this assignment fails with TypeError
                # TODO atomsgroup_ref is now only in RadiiOfGyration, assess
                # relevance in both classes
                # try:
                #     sec_rgs_out.atomsgroup_ref = [rg.get('atomsgroup_ref')]
                # except Exception:
                #     pass
                sec_rgs_out.label = rg.get('label')
                sec_rgs_out.value = rg.get('value')[sys_ind]

    @log
    def get_molecular_rgs(
        self,
        archive: EntryArchive,
    ) -> list[RadiiOfGyration]:
        """
        Calculate and return radius of gyration data for the workflow.
        Also populates the corresponding output sections in the archive.
        """
        logger = self.get_molecular_rgs.__annotations__['logger']

        # Check if already calculated
        if self.radii_of_gyration:
            return self.radii_of_gyration

        try:
            data = archive.data
            sec_systems = data.system
            sec_system = sec_systems[data.representative_system_index]
            sec_outputs = data.outputs
        except Exception:
            logger.warning('Could not access archive data for RG calculation')
            return []

        # Check if RGs are already present in outputs
        flag_rgs = False
        for out in sec_outputs:
            if hasattr(out, 'radii_of_gyration') and out.radii_of_gyration:
                flag_rgs = True
                break  # TODO Should transfer Rg's to workflow results if they are already supplied in calculation

        workflow_rgs = []

        if not flag_rgs:  # Calculate RGs if not already present
            if self._universe is None:
                logger.warning('Universe is None, cannot calculate RGs')
                return []

            system_hierarchy = sec_system.sub_systems
            rg_results = calc_molecular_rg(self._universe, system_hierarchy)

            # Create workflow RG sections
            for rg in rg_results:
                sec_rgs = RadiiOfGyration()  # Use plural name for trajectory workflow
                sec_rgs._rg_results = rg
                workflow_rgs.append(sec_rgs)

            # Populate output sections separately
            self._populate_output_rgs(archive, rg_results, logger)

        return workflow_rgs

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        self._universe = self.get_universe(archive)
        if self._universe is None:
            return

        self._bead_groups = _get_molecular_bead_groups(self._universe)

        # calculate molecular radial distribution functions
        self.radial_distribution_functions.extend(self._get_molecular_rdfs(archive))

        # calculate the molecular mean squared displacements
        msds, diffusion_constants = self._get_molecular_msds()
        self.mean_squared_displacements.extend(msds)
        self.diffusion_constants.extend(diffusion_constants)

        # calculate radius of gyration for polymers
        self.radii_of_gyration = self.get_molecular_rgs(archive)


class MolecularDynamics(SerialWorkflow):
    _task_label = 'Step'

    method = SubSection(sub_section=MolecularDynamicsMethod)

    results = SubSection(sub_section=MolecularDynamicsResults)

    def map_inputs(self, archive: EntryArchive, logger: BoundLogger = None) -> None:
        super().map_inputs(archive, logger)
        if not self.method:
            self.method = MolecularDynamicsMethod()

    def map_outputs(self, archive: EntryArchive, logger: BoundLogger = None) -> None:
        if not self.results:
            self.results = MolecularDynamicsResults()
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if not self.method:
            self.method = MolecularDynamicsMethod()

        if not self.results:
            self.results = MolecularDynamicsResults()
