from typing import TYPE_CHECKING, Optional

import numpy as np
import pint
from nomad.config import config
from nomad.metainfo import MEnum, Quantity, SubSection

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import AtomsState, OrbitalsState
from nomad_simulations.schema_packages.data_types import positive_float
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties.band_gap import ElectronicBandGap
from nomad_simulations.schema_packages.utils import get_sibling_section, log
from nomad_simulations.schema_packages.variables import Energy2 as Energy

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


class SpectralProfile(PhysicalProperty):
    """
    A base section used to define the spectral profile.
    """

    value = Quantity(
        type=positive_float(),
        shape=['*'],
        description="""
        The value of the intensities of a spectral profile. Must be positive.
        """,
    )  # TODO check units and normalization_factor of DOS and Spectra and see whether they can be merged

    energies = SubSection(sub_section=Energy.m_def)

    frequencies = SubSection(sub_section=Energy.m_def)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class DOSProfile(SpectralProfile):
    """
    A base section used to define the `value` of the `ElectronicDensityOfState` property. This is useful when containing
    contributions for `projected_dos` with the correct unit.
    """

    value = Quantity(
        type=positive_float(),
        unit='1/joule',
        shape=['*'],
        description="""
        The value of the electronic DOS. Must be positive.
        """,
    )

    energies = SubSection(
        sub_section=Energy.m_def,
        description="""
        Energy grid points of the projected electronic DOS.
        """,
    )

    @log
    def resolve_pdos_name(self) -> str | None:
        """
        Resolve the `name` of the projected `DOSProfile` from the `entity_ref` section. This is resolved as:
            - `'atom X'` with 'X' being the chemical symbol for `AtomsState` references.
            -  `'orbital Y X'` with 'X' being the chemical symbol and 'Y' the orbital label for `OrbitalsState` references.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[str]): The resolved `name` of the projected DOS profile.
        """
        logger = self.resolve_pdos_name.__annotations__['logger']
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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # We resolve
        self.name = self.resolve_pdos_name(logger=logger)


class ElectronicDensityOfStates(DOSProfile):
    """
    Number of electronic states accessible for the charges per energy and per volume.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicDensityOfStates'

    spin_channel = Quantity(
        type=np.int32,
        description="""
        Spin channel of the corresponding electronic DOS. It can take values of 0 or 1.
        """,
    )

    # TODO clarify the role of `energies_origin` once `ElectronicEigenvalues` is implemented
    energies_origin = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Energy level denoting the origin along the energy axis, used for comparison and visualization. It is
        defined as the `ElectronicEigenvalues.highest_occupied_energy`.
        """,
    )

    normalization_factor = Quantity(
        type=np.float64,
        description="""
        Normalization factor for electronic DOS to get a cell-independent intensive DOS. The cell-independent
        intensive DOS is as the integral from the lowest (most negative) energy to the Fermi level for a neutrally
        charged system (i.e., the sum of `AtomsState.charge` is zero).
        """,
    )

    # ? Do we want to store the integrated value here os as part of an nomad-analysis tool? Check `dos_integrator.py` module in dos normalizer repository
    # value_integrated = Quantity(
    #     type=np.float64,
    #     description="""
    #     The cumulative intensities integrated from from the lowest (most negative) energy to the Fermi level.
    #     """,
    # )

    energies = SubSection(
        sub_section=Energy.m_def,
        description="""
        Energy grid points of the electronic DOS.
        """,
    )  # ? convert to `Quantity`

    projected_dos = SubSection(
        sub_section=DOSProfile.m_def,
        repeats=True,
        description="""
        Projected DOS. It can be atom- (different elements in the unit cell) or orbital-projected. These can be calculated in a cascade as:
            - If the total DOS is not present, we sum all atom-projected DOS to obtain it.
            - If the atom-projected DOS is not present, we sum all orbital-projected DOS to obtain it.
        Note: the cover given by summing up contributions is not perfect, and will depend on the projection functions used.

        In `projected_dos`, `name` and `entity_ref` must be set in order for normalization to work:
            - The `entity_ref` is the `OrbitalsState` or `AtomsState` sections.
            - The `name` of the projected DOS should be `'atom X'` or `'orbital Y X'`, with 'X' being the chemical symbol and 'Y' the orbital label.
            These can be extracted from `entity_ref`.
        """,
    )

    def resolve_energies_origin(
        self,
        energies_points: pint.Quantity,
        fermi_level: pint.Quantity | None,
        logger: 'BoundLogger',
    ) -> pint.Quantity | None:
        """
        Resolve the origin of reference for the energies from the sibling `ElectronicEigenvalues` section and its
        `highest_occupied` level, or if this does not exist, from the `fermi_level` value as extracted from the sibling property, `FermiLevel`.

        Args:
            fermi_level (Optional[pint.Quantity]): The resolved Fermi level.
            energies_points (pint.Quantity): The grid points of the `Energy` variable.
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[pint.Quantity]): The resolved origin of reference for the energies.
        """

        # Extract the `ElectronicEigenvalues` section to get the `highest_occupied` and `lowest_unoccupied` energies
        # TODO implement once `ElectronicEigenvalues` is in the schema
        eigenvalues = get_sibling_section(
            section=self, sibling_section_name='electronic_eigenvalues', logger=logger
        )  # we consider `index_sibling` to be 0
        highest_occupied_energy = (
            eigenvalues.highest_occupied if eigenvalues is not None else None
        )
        lowest_unoccupied_energy = (
            eigenvalues.lowest_unoccupied if eigenvalues is not None else None
        )
        # and set defaults for `highest_occupied_energy` and `lowest_unoccupied_energy` in `m_cache`
        if highest_occupied_energy is not None:
            self.m_cache['highest_occupied_energy'] = highest_occupied_energy
        if lowest_unoccupied_energy is not None:
            self.m_cache['lowest_unoccupied_energy'] = lowest_unoccupied_energy

        # Check that the closest `energies` to the energy reference is not too far away.
        # If it is very far away, normalization may be very inaccurate and we do not report it.
        dos_values = self.value.magnitude
        eref = highest_occupied_energy if fermi_level is None else fermi_level
        fermi_idx = (np.abs(energies_points - eref)).argmin()
        fermi_energy_closest = energies_points[fermi_idx]
        distance = np.abs(fermi_energy_closest - eref)
        single_peak_fermi = False
        if distance.magnitude <= configuration.dos_energy_tolerance:
            # See if there are zero values close below the energy reference.
            idx = fermi_idx
            idx_descend = fermi_idx
            while True:
                try:
                    value = dos_values[idx]
                    energy_distance = np.abs(eref - energies_points[idx])
                except IndexError:
                    break
                if energy_distance.magnitude > configuration.dos_energy_tolerance:
                    break
                if value <= configuration.dos_intensities_threshold:
                    idx_descend = idx
                    break
                idx -= 1

            # See if there are zero values close above the fermi energy.
            idx = fermi_idx
            idx_ascend = fermi_idx
            while True:
                try:
                    value = dos_values[idx]
                    energy_distance = np.abs(eref - energies_points[idx])
                except IndexError:
                    break
                if energy_distance.magnitude > configuration.dos_energy_tolerance:
                    break
                if value <= configuration.dos_intensities_threshold:
                    idx_ascend = idx
                    break
                idx += 1

            # If there is a single peak at fermi energy, no
            # search needs to be performed.
            if idx_ascend != fermi_idx and idx_descend != fermi_idx:
                self.m_cache['highest_occupied_energy'] = fermi_energy_closest
                self.m_cache['lowest_unoccupied_energy'] = fermi_energy_closest
                single_peak_fermi = True

            if not single_peak_fermi:
                # Look for highest occupied energy below the descend index
                idx = idx_descend
                while True:
                    try:
                        value = dos_values[idx]
                    except IndexError:
                        break
                    if value > configuration.dos_intensities_threshold:
                        idx = idx if idx == idx_descend else idx + 1
                        self.m_cache['highest_occupied_energy'] = energies_points[idx]
                        break
                    idx -= 1
                # Look for lowest unoccupied energy above idx_ascend
                idx = idx_ascend
                while True:
                    try:
                        value = dos_values[idx]
                    except IndexError:
                        break
                    if value > configuration.dos_intensities_threshold:
                        idx = idx if idx == idx_ascend else idx - 1
                        self.m_cache['highest_occupied_energy'] = energies_points[idx]
                        break
                    idx += 1

        # Return the `highest_occupied_energy` as the `energies_origin`, or the `fermi_level` if it is not None
        energies_origin = self.m_cache.get('highest_occupied_energy')
        if energies_origin is None:
            energies_origin = fermi_level
        return energies_origin

    @log
    def resolve_normalization_factor(self) -> float | None:
        """
        Resolve the `normalization_factor` for the electronic DOS to get a cell-independent intensive DOS.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[float]): The normalization factor.
        """
        logger = self.resolve_normalization_factor.__annotations__['logger']
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

        atomic_numbers = [atom.atomic_number for atom in model_system.particle_states]

        # Compute normalization_factor. If spin_channel is set, assume spin-polarized system.
        if self.spin_channel is not None:
            normalization_factor = 1 / (2 * sum(atomic_numbers))
        else:
            normalization_factor = 1 / sum(atomic_numbers)
        return normalization_factor

    def extract_band_gap(self) -> ElectronicBandGap | None:
        """
        Extract the electronic band gap from the `highest_occupied_energy` and `lowest_unoccupied_energy` stored
        in `m_cache` from `resolve_energies_origin()`. If the difference of `highest_occupied_energy` and
        `lowest_unoccupied_energy` is negative, the band gap `value` is set to 0.0.

        Returns:
            (Optional[ElectronicBandGap]): The extracted electronic band gap section to be stored in `Outputs`.
        """
        band_gap = None
        homo = self.m_cache.get('highest_occupied_energy')
        lumo = self.m_cache.get('lowest_unoccupied_energy')
        if homo and lumo:
            band_gap = ElectronicBandGap()
            band_gap.is_derived = True
            band_gap.physical_property_ref = self

            if (homo - lumo).magnitude < 0:
                band_gap.value = 0.0
            else:
                band_gap.value = homo - lumo
        return band_gap

    def extract_projected_dos(
        self, type: str, logger: 'BoundLogger'
    ) -> list[DOSProfile | None]:
        """
        Extract the projected DOS from the `projected_dos` section and the specified `type`.

        Args:
            type (str): The type of the projected DOS to extract. It can be `'atom'` or `'orbital'`.

        Returns:
            (DOSProfile): The extracted projected DOS.
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

    def generate_from_projected_dos(
        self, logger: 'BoundLogger'
    ) -> pint.Quantity | None:
        """
        Generate the total `value` of the electronic DOS from the `projected_dos` contributions. If the `projected_dos`
        is not present, it returns `None`.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[pint.Quantity]): The total `value` of the electronic DOS.
        """
        if self.projected_dos is None or len(self.projected_dos) == 0:
            return None

        # We distinguish between orbital and atom `projected_dos`
        orbital_projected = self.extract_projected_dos('orbital', logger)
        atom_projected = self.extract_projected_dos('atom', logger)

        # if we only have orbital entries, build atom entries
        orbital_projected = self.extract_projected_dos('orbital', logger)
        atom_projected = self.extract_projected_dos('atom', logger)

        if not atom_projected:
            # group orbitals by their AtomsState
            atom_orbital_map: dict[AtomsState, list[DOSProfile]] = {}
            for orb in orbital_projected:
                parent = getattr(orb.entity_ref, 'm_parent', None)
                if isinstance(parent, AtomsState):
                    atom_orbital_map.setdefault(parent, []).append(orb)

            for atom_state, orbs in atom_orbital_map.items():
                # sum their values
                vals = [o.value.magnitude for o in orbs]
                unit = orbs[0].value.u
                pd = DOSProfile(
                    entity_ref=atom_state,
                    energies=self.energies,
                )
                pd.name = f'atom {atom_state.chemical_symbol}'
                pd.value = np.sum(vals, axis=0) * unit
                atom_projected.append(pd)

            # now store the full projected list
            self.projected_dos = orbital_projected + atom_projected

        # finally compute or reuse self.value
        if self.value is None:
            vals = [pd.value.magnitude for pd in atom_projected]
            unit = atom_projected[0].value.u
            self.value = np.sum(vals, axis=0) * unit

        return self.value

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Initial check to see whether `energies` is defined
        if self.energies is None:
            return

        # Resolve `fermi_level` from a sibling section with respect to `ElectronicDensityOfStates`
        fermi_level = get_sibling_section(
            section=self, sibling_section_name='fermi_level', logger=logger
        )  # * we consider `index_sibling` to be 0
        if fermi_level is not None:
            fermi_level = fermi_level.value
        # and the `energies_origin` from the sibling `ElectronicEigenvalues` section
        self.energies_origin = self.resolve_energies_origin(
            self.energies.points, fermi_level, logger
        )
        if self.energies_origin is None:
            logger.info('Could not resolve the `energies_origin` for the DOS')

        # Resolve `normalization_factor`
        if self.normalization_factor is None:
            self.normalization_factor = self.resolve_normalization_factor(logger=logger)

        # `ElectronicBandGap` extraction
        band_gap = self.extract_band_gap()
        if band_gap is not None:
            self.m_parent.electronic_band_gap.append(band_gap)

        # Total `value` extraction from `projected_dos`
        value_from_pdos = self.generate_from_projected_dos(logger)
        if self.value is None and value_from_pdos is not None:
            logger.info(
                'The `ElectronicDensityOfStates.value` is not stored. We will attempt to obtain it by summing up projected DOS contributions, if these are present.'
            )
            self.value = value_from_pdos


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

    @log
    def generate_from_contributions(self) -> None:
        """
        Generate the `value` of the XAS spectrum by concatenating the XANES and EXAFS contributions. It also concatenates
        the `Energy` grid points of the XANES and EXAFS parts.

        Args:
            logger (BoundLogger): The logger to log messages.
        """
        logger = self.generate_from_contributions.__annotations__['logger']
        # TODO check if this method is general enough
        if self.xanes_spectrum is not None and self.exafs_spectrum is not None:
            # Concatenate XANE and EXAFS `Energy` grid points
            xanes_variables = self.xanes_spectrum.energies
            exafs_variables = self.exafs_spectrum.energies
            if len(xanes_variables) == 0 or len(exafs_variables) == 0:
                logger.warning(
                    'Could not extract the `Energy` grid points from XANES or EXAFS.'
                )
                return
            xanes_energies = xanes_variables.points
            exafs_energies = exafs_variables.points
            if xanes_energies.max() > exafs_energies.min():
                logger.warning(
                    'The XANES `Energy` grid points are not below the EXAFS `Energy` grid points.'
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
            self.generate_from_contributions(logger=logger)
