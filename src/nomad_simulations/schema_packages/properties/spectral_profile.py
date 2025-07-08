from typing import TYPE_CHECKING, Optional

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from nomad.config import config
from nomad.datamodel.metainfo.plot import PlotlyFigure
from nomad.metainfo import MEnum, Quantity, SubSection
from nomad.units import ureg

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import AtomsState, OrbitalsState
from nomad_simulations.schema_packages.data_types import positive_float
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.utils import get_sibling_section
from nomad_simulations.schema_packages.utils.utils import check_not_none, inner_copy
from nomad_simulations.schema_packages.variables import Energy2 as Energy

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


class SpectralProfile(PhysicalProperty):
    """
    A base section used to define the spectral profile.
    """

    energies = Quantity(
        type=np.float64,
        unit='joule',
        shape=['*'],
        description="""
        Energy sampling.
        """,
    )

    frequencies = Quantity(
        type=np.float64,
        unit='hertz',
        shape=['*'],
        description="""
        Frequency sampling.
        """,
    )


class ElectronicDensityOfStates(SpectralProfile):
    """
    A base section used to define the `value` of the `ElectronicDensityOfState` property. This is useful when containing
    contributions for `projected_dos` with the correct unit.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicDensityOfStates'

    value = Quantity(
        type=positive_float(dtype=np.float64),
        unit='1/joule',
        shape=['spin', '*'],
        description="""
        The value of the electronic DOS.
        """,
    )

    normalization_factor = Quantity(
        type=np.float64,
        description="""
        Normalization factor for electronic DOS, converting from an extensive to an intensive quantity.
        The intensive DOS is defined as the integral from the lowest (most negative) energy to the highest occupied energy
        for a neutral system (i.e., the sum of `AtomsState.charge` is zero).
        """,
    )  # This requires knowing the units of the parsed DOS

    def resolve_pdos_name(self, logger: 'BoundLogger') -> Optional[str]:
        """
        Resolve the `name` of the projected `DOSProfile` from the `entity_ref` section. This is resolved as:
            - `'atom X'` with 'X' being the chemical symbol for `AtomsState` references.
            -  `'orbital Y X'` with 'X' being the chemical symbol and 'Y' the orbital label for `OrbitalsState` references.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[str]): The resolved `name` of the projected DOS profile.
        """
        if self.entity_ref is None and not self.name == 'ElectronicDensityOfStates':
            logger.warning(
                'The `entity_ref` is not set for the DOS profile. Could not resolve the `name`.'
            )
            return None

        if self.entity_ref is None:
            logger.warning('No entity_ref on DOSProfile; cannot name it.')
            return None

        # Atom‐projected DOS
        if isinstance(self.entity_ref, AtomsState):
            elem = self.entity_ref.chemical_symbol
            if elem:
                return f'atom {elem}'
            else:
                logger.warning('AtomsState missing chemical_symbol.')
                return None

        # Orbital‐projected DOS
        if isinstance(self.entity_ref, OrbitalsState):
            # navigate up to the parent AtomsState
            parent = getattr(self.entity_ref, 'm_parent', None)
            if not isinstance(parent, AtomsState) or not parent.chemical_symbol:
                logger.warning('Could not find parent AtomsState with chemical_symbol.')
                return None

            l_label = (
                f'{self.entity_ref.l_quantum_symbol}{self.entity_ref.ml_quantum_symbol}'
            )
            return f'orbital {l_label} {parent.chemical_symbol}'

        # other cases
        logger.warning(
            f'Unknown entity_ref type {type(self.entity_ref)}; cannot name PDOS.'
        )
        return None

    def resolve_normalization_factor(self, logger: 'BoundLogger') -> Optional[float]:
        """
        Resolve the `normalization_factor` for the electronic DOS to get a cell-independent intensive DOS.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[float]): The normalization factor.
        """
        model_system = get_sibling_section(
            section=self, sibling_section_name='model_system_ref', logger=logger
        )
        if model_system is None:
            logger.warning(
                'Could not resolve the referenced `ModelSystem` in the `Outputs`.'
            )
            return None

        # Instead of self.m_parent, use model_system for particle_states
        if (
            model_system.particle_states is None
            or len(model_system.particle_states) == 0
        ):
            logger.warning(
                'Could not resolve the `particle_states` from the referenced ModelSystem.'
            )
            return None

        return 1 / sum([atom.atomic_number for atom in model_system.particle_states])

    def extract_projected_dos(
        self, type: str, logger: 'BoundLogger'
    ) -> 'list[ElectronicDensityOfStates | None]':
        """
        Extract the projected DOS from the `projected_dos` section and the specified `type`.

        Args:
            type (str): The type of the projected DOS to extract. It can be `'atom'` or `'orbital'`.

        Returns:
            (ElectronicDensityOfStates): The extracted projected DOS.
        """
        extracted_pdos = []
        for pdos in self.projected_dos:
            # We make sure each PDOS is normalized
            pdos.normalize(None, logger)

            # Initial check for `name` and `entity_ref`
            if pdos.name is None or pdos.entity_ref is None:
                logger.warning(
                    '`name` or `entity_ref` are not set for `projected_dos` and they are required for normalization to work.'
                )
                return None

            if type in pdos.name:
                extracted_pdos.append(pdos)
        return extracted_pdos

    @check_not_none('self.value')
    def pad_out(self) -> None:
        """
        Pad out the value and energies arrays along the spin channel dimension.
        """
        spin_index = 0  # Spin is first dimension
        if np.array(self.value).shape[spin_index] == 1:
            self.value = inner_copy(self.value, 0)

    @check_not_none('self.value', 'self.energies')
    def plot(self, *args, **kwargs) -> list['PlotlyFigure']:
        """
        Plot the electronic density of states.
        
        Returns:
            list['PlotlyFigure']: A list containing the DOS plot figure(s).
        """
        fig = go.Figure()
        energies_ev = self.energies.to('eV').magnitude
        dos_values = self.value.to('1/eV').magnitude

        # Spin up (positive)
        fig.add_trace(go.Scatter(
            x=energies_ev,
            y=dos_values[0],
            mode='lines',
            name='Spin up',
            line=dict(color='blue')
        ))
        
        # Spin down (negative for traditional representation)
        fig.add_trace(go.Scatter(
            x=energies_ev,
            y=-dos_values[1],
            mode='lines',
            name='Spin down',
            line=dict(color='red')
        ))
        
        fig.update_layout(
            title=f"Electronic Density of States{' - ' + self.name if self.name else ''}",
            xaxis_title='Energy (eV)',
            yaxis_title='DOS (states/eV)',
            showlegend=True,
            hovermode='x'
        )
        
        # Add horizontal line at y=0
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        # Add vertical line at Fermi level if available
        # Note: You might want to get Fermi energy from model_method or similar
        # fig.add_vline(x=fermi_energy, line_dash="dash", line_color="green", 
        #               annotation_text="E_F")
        
        return [
            PlotlyFigure(
                label=f'DOS{" - " + self.name if self.name else ""}',
                figure=fig.to_plotly_json()
            )
        ]

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        # self.name = self.resolve_pdos_name(logger)
        self.pad_out()

        if self.normalization_factor is None:
            self.normalization_factor = self.resolve_normalization_factor(logger)

        super().normalize(archive, logger)


class AbsorptionSpectrum(SpectralProfile):
    """ """

    axis = Quantity(
        type=MEnum('xx', 'yy', 'zz'),
        description="""
        Axis of the absorption spectrum. This is related with the polarization direction, and can be seen as the
        principal term in the tensor `Permittivity.value` (see permittivity.py module).
        """,
    )


class XASSpectrum(AbsorptionSpectrum):
    """
    X-ray Absorption Spectrum (XAS).
    """

    xanes_spectrum = SubSection(
        sub_section=AbsorptionSpectrum.m_def,
        description="""
        X-ray Absorption Near Edge Structure (XANES) spectrum.
        """,
        repeats=False,
    )

    exafs_spectrum = SubSection(
        sub_section=AbsorptionSpectrum.m_def,
        description="""
        Extended X-ray Absorption Fine Structure (EXAFS) spectrum.
        """,
        repeats=False,
    )

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)
        # Set the name of the section
        self.name = self.m_def.name

    def generate_from_contributions(self, logger: 'BoundLogger') -> None:
        """
        Generate the `value` of the XAS spectrum by concatenating the XANES and EXAFS contributions. It also concatenates
        the `Energy` grid of the XANES and EXAFS parts.

        Args:
            logger (BoundLogger): The logger to log messages.
        """
        # TODO check if this method is general enough
        if self.xanes_spectrum is not None and self.exafs_spectrum is not None:
            # Concatenate XANE and EXAFS `Energy` grid
            xanes_variables = self.xanes_spectrum.energies
            exafs_variables = self.exafs_spectrum.energies
            if len(xanes_variables) == 0 or len(exafs_variables) == 0:
                logger.warning(
                    'Could not extract the `Energy` grid from XANES or EXAFS.'
                )
                return
            xanes_energies = xanes_variables
            exafs_energies = exafs_variables
            if xanes_energies.max() > exafs_energies.min():
                logger.warning(
                    'The XANES `Energy` grid is not below the EXAFS `Energy` grid.'
                )
                return
            self.energies = Energy(
                points=np.concatenate([xanes_energies, exafs_energies])
            )
            # Concatenate XANES and EXAFS `value` if they have the same shape ['n_energies']  # ? what about the variables
            try:
                self.value = np.concatenate(
                    [self.xanes_spectrum.value, self.exafs_spectrum.value]
                )
            except ValueError:
                logger.warning(
                    'The XANES and EXAFS `value` have different shapes. Could not concatenate the values.'
                )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        if self.value is None:
            logger.info(
                'The `XASSpectrum.value` is not stored. We will attempt to obtain it by combining the XANES and EXAFS parts if these are present.'
            )
            self.generate_from_contributions(logger)
