import numpy as np
import pytest
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties import (
    AbsorptionSpectrum,
    DOSProfile,
    ElectronicDensityOfStates,
    XASSpectrum,
)
from nomad_simulations.schema_packages.properties.electronic_eigenvalues import (
    ElectronicEigenvalues,
)
from nomad_simulations.schema_packages.variables import Energy2 as Energy

from . import logger


class TestElectronicDensityOfStates:
    """
    Test the `ElectronicDensityOfStates` class defined in `properties/spectral_profile.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    def test_default_quantities(self):
        """
        Test the default quantities assigned when creating an instance of the `ElectronicDensityOfStates` class.
        """
        electronic_dos = ElectronicDensityOfStates()
        assert (
            electronic_dos.iri
            == 'http://fairmat-nfdi.eu/taxonomy/ElectronicDensityOfStates'
        )

    def _dos_with_reference(self, dos_values, highest_occupied):
        """
        Build an `ElectronicDensityOfStates` attached to an `Outputs` parent that also holds an
        `ElectronicEigenvalues` sibling. When `highest_occupied` is None the sibling exposes no
        reference, so `resolve_energies_origin` returns None; otherwise it sets `highest_occupied`.
        This mirrors production, where the origin is resolved internally (no parsed Fermi-level
        fallback).
        """
        outputs = Outputs()
        electronic_dos = ElectronicDensityOfStates()
        electronic_dos.value = dos_values * ureg('1/joule')
        outputs.electronic_dos.append(electronic_dos)
        eigenvalues = ElectronicEigenvalues()
        if highest_occupied is not None:
            eigenvalues.highest_occupied = highest_occupied
        outputs.electronic_eigenvalues.append(eigenvalues)
        return electronic_dos

    @pytest.mark.parametrize(
        'dos_values, highest_occupied, expected_origin, expected_homo, expected_lumo',
        [
            # gapped DOS: valence <= -0.20 eV, conduction >= 0.30 eV, reference in the gap
            pytest.param(
                np.concatenate([np.ones(31), np.zeros(49), np.ones(21)]),
                0.0 * ureg.eV,
                -0.20,
                -0.20,
                0.30,
                id='gapped',
            ),
            # metallic DOS: finite across the reference -> HOMO == LUMO == reference
            pytest.param(np.ones(101), 0.0 * ureg.eV, 0.0, 0.0, 0.0, id='metallic'),
            # only unoccupied states: HOMO stays at the reference, LUMO at the band edge
            pytest.param(
                np.concatenate([np.zeros(80), np.ones(21)]),
                0.0 * ureg.eV,
                0.0,
                0.0,
                0.30,
                id='without_occupied',
            ),
            # reference farther than `dos_energy_tolerance` from the grid -> no origin
            pytest.param(
                np.ones(101), 10.0 * ureg.eV, None, 10.0, None, id='outside_window'
            ),
            # no resolvable reference on the sibling -> no origin
            pytest.param(np.ones(101), None, None, None, None, id='no_reference'),
        ],
    )
    def test_resolve_energies_origin(
        self,
        dos_values,
        highest_occupied,
        expected_origin,
        expected_homo,
        expected_lumo,
    ):
        """
        Resolve the DOS energy origin from the sibling `ElectronicEigenvalues.highest_occupied`.

        The DOS grid runs from -0.5 to 0.5 eV. Expected values are in eV, or None when nothing is
        resolved. `highest_occupied=None` means the sibling exposes no reference.
        """
        energies_points = np.linspace(-0.5, 0.5, 101) * ureg.eV
        electronic_dos = self._dos_with_reference(dos_values, highest_occupied)

        energies_origin = electronic_dos.resolve_energies_origin(
            energies_points=energies_points,
            logger=logger,
        )

        def _matches(actual, expected):
            if expected is None:
                return actual is None
            return actual is not None and np.isclose(
                actual.to('eV').magnitude, expected, atol=1e-9
            )

        assert _matches(energies_origin, expected_origin)
        assert _matches(
            electronic_dos.m_cache.get('highest_occupied_energy'), expected_homo
        )
        assert _matches(
            electronic_dos.m_cache.get('lowest_unoccupied_energy'), expected_lumo
        )

    @pytest.mark.parametrize(
        'dos_values, highest_occupied, expected_gap',
        [
            pytest.param(
                np.concatenate([np.ones(31), np.zeros(49), np.ones(21)]),
                0.0 * ureg.eV,
                0.50,
                id='gapped',
            ),
            # regression: a gap of exactly 0 eV must not be discarded by `extract_band_gap`
            pytest.param(np.ones(101), 0.0 * ureg.eV, 0.0, id='metallic'),
        ],
    )
    def test_resolve_energies_origin_band_gap(
        self, dos_values, highest_occupied, expected_gap
    ):
        """
        The DOS-derived band gap from the cached HOMO/LUMO after resolving the energy origin.
        """
        energies_points = np.linspace(-0.5, 0.5, 101) * ureg.eV
        electronic_dos = self._dos_with_reference(dos_values, highest_occupied)
        electronic_dos.resolve_energies_origin(
            energies_points=energies_points,
            logger=logger,
        )

        band_gap = electronic_dos.extract_band_gap()
        assert band_gap is not None
        assert np.isclose(band_gap.value.to('eV').magnitude, expected_gap, atol=1e-9)

    def test_resolve_normalization_factor(self, simulation_electronic_dos: Simulation):
        """
        Test the `resolve_normalization_factor` method.

        Note: This test uses the fixture directly to preserve the metainfo parent relationships
        established during outputs.normalize(). The resolve_normalization_factor() method relies
        on get_sibling_section() which uses XPath traversal (m_parent.model_system_ref), so
        proper parent linkages are essential for the test to work correctly.
        """
        # Use the fixture which has properly normalized structure with model_system_ref set
        outputs = simulation_electronic_dos.outputs[0]
        electronic_dos = outputs.electronic_dos[0]
        model_system = outputs.model_system_ref

        # Save original state
        original_particles = model_system.particle_states
        original_spin = electronic_dos.spin_channel

        # Set up particle_states with known atomic numbers for testing
        particle_states = [AtomsState() for _ in range(2)]
        particle_states[0].__dict__['atomic_number'] = 31  # Ga
        particle_states[1].__dict__['atomic_number'] = 33  # As
        model_system.particle_states = particle_states

        # Non spin-polarized: normalization factor is 1 / (sum of atomic numbers)
        normalization_factor = electronic_dos.resolve_normalization_factor(
            logger=logger
        )
        expected = 1.0 / (31 + 33)
        assert np.isclose(normalization_factor, expected)

        # Spin-polarized: normalization factor is 1 / (2 * sum of atomic numbers)
        electronic_dos.spin_channel = 0
        normalization_factor_spin = electronic_dos.resolve_normalization_factor(
            logger=logger
        )
        expected_spin = 1.0 / (2 * (31 + 33))
        assert np.isclose(normalization_factor_spin, expected_spin)

        # Restore original state
        model_system.particle_states = original_particles
        electronic_dos.spin_channel = original_spin

    @pytest.mark.parametrize(
        'homo, lumo, result',
        [
            # gapped system
            (1.0, 2.0, 1.0),
            # overlapping bands: negative difference is clamped to 0
            (2.0, 1.0, 0.0),
            # HOMO exactly at 0 eV must not be skipped (regression for truthiness check)
            (0.0, 1.0, 1.0),
            # missing either energy reference means no derived band gap
            (None, 1.0, None),
            (1.0, None, None),
            (None, None, None),
        ],
    )
    def test_extract_band_gap(
        self, homo: float | None, lumo: float | None, result: float | None
    ):
        """
        Test the `extract_band_gap` method from the `highest_occupied_energy` and
        `lowest_unoccupied_energy` values stored in `m_cache`.
        """
        electronic_dos = ElectronicDensityOfStates()
        if homo is not None:
            electronic_dos.m_cache['highest_occupied_energy'] = homo * ureg.eV
        if lumo is not None:
            electronic_dos.m_cache['lowest_unoccupied_energy'] = lumo * ureg.eV

        band_gap = electronic_dos.extract_band_gap()
        if result is None:
            assert band_gap is None
        else:
            assert band_gap.is_derived
            assert band_gap.physical_property_ref == electronic_dos
            assert np.isclose(band_gap.value.to('eV').magnitude, result)

    def test_resolve_pdos_name(self, simulation_electronic_dos: Simulation):
        """
        Test the `resolve_pdos_name` method.
        """
        # Get projected DOSProfile from the simulation fixture
        projected_dos = (
            simulation_electronic_dos.outputs[0].electronic_dos[0].projected_dos
        )
        assert len(projected_dos) == 3
        pdos_names = ['orbital s Ga', 'orbital px As', 'orbital py As']
        for i, pdos in enumerate(projected_dos):
            name = pdos.resolve_pdos_name(logger=logger)
            assert name == pdos_names[i]

    def test_resolve_pdos_name_missing_entity_ref_no_exception(self):
        """Missing entity_ref should return None without decorator exception warnings."""
        parent = ElectronicDensityOfStates()
        pdos = DOSProfile()
        parent.projected_dos.append(pdos)

        assert pdos.resolve_pdos_name(logger=logger) is None

    def test_extract_projected_dos(self, simulation_electronic_dos: Simulation):
        """
        Test the `extract_projected_dos` method.
        """
        # Get Outputs and ElectronicDensityOfStates from the simulation fixture
        outputs = simulation_electronic_dos.outputs[0]
        electronic_dos = outputs.electronic_dos[0]

        # Initial tests for the passed `projected_dos` (only orbital PDOS)
        assert len(electronic_dos.projected_dos) == 3  # only orbital projected DOS
        orbital_projected = electronic_dos.extract_projected_dos('orbital', logger)
        atom_projected = electronic_dos.extract_projected_dos('atom', logger)
        assert len(orbital_projected) == 3 and len(atom_projected) == 0
        orbital_projected_names = [orb_pdos.name for orb_pdos in orbital_projected]
        assert orbital_projected_names == [
            'orbital s Ga',
            'orbital px As',
            'orbital py As',
        ]
        assert (
            orbital_projected[0].entity_ref
            == outputs.model_system_ref.particle_states[0].electronic_state.sub_states[
                0
            ]
        )
        assert (
            orbital_projected[1].entity_ref
            == outputs.model_system_ref.particle_states[1].electronic_state.sub_states[
                0
            ]
        )
        # For the third orbital, assume it comes from the second particle as well (e.g. As atom has two orbitals)
        assert (
            orbital_projected[2].entity_ref
            == outputs.model_system_ref.particle_states[1].electronic_state.sub_states[
                1
            ]
        )

        # Run extraction again to verify repeatability
        orbital_projected = electronic_dos.extract_projected_dos('orbital', logger)
        atom_projected = electronic_dos.extract_projected_dos('atom', logger)
        assert len(orbital_projected) == 3 and len(atom_projected) == 0

    @pytest.mark.parametrize(
        'value, result',
        [
            (None, [1.5, 1.2, 0, 0, 0, 0.8, 1.3]),
            ([30.5, 1.2, 0, 0, 0, 0.8, 1.3], [30.5, 1.2, 0, 0, 0, 0.8, 1.3]),
        ],
    )
    def test_generate_from_pdos(
        self,
        simulation_electronic_dos: Simulation,
        value: list[float] | None,
        result: list[float],
    ):
        """
        Test the `generate_from_projected_dos` method.
        """
        # Get Outputs and ElectronicDensityOfStates from the simulation fixture
        outputs = simulation_electronic_dos.outputs[0]
        electronic_dos = outputs.electronic_dos[0]

        # Add `value`
        if value is not None:
            electronic_dos.value = value * ureg('1/joule')

        val = electronic_dos.generate_from_projected_dos(logger)
        assert (val.magnitude == result).all()

        # Testing both orbital and atom projected DOS: expect 5 entries (3 orbitals + 2 atoms)
        assert len(electronic_dos.projected_dos) == 5
        orbital_projected = electronic_dos.extract_projected_dos('orbital', logger)
        atom_projected = electronic_dos.extract_projected_dos('atom', logger)
        assert len(orbital_projected) == 3 and len(atom_projected) == 2
        atom_projected_names = [ap.name for ap in atom_projected]
        assert atom_projected_names == ['atom Ga', 'atom As']
        # Check that the entity_ref of the atom PDOS points to the ElectronicState (not AtomsState)
        # This is the new architectural pattern where ElectronicState serves as gateway
        assert (
            atom_projected[0].entity_ref
            == outputs.model_system_ref.particle_states[0].electronic_state
        )
        assert (
            atom_projected[1].entity_ref
            == outputs.model_system_ref.particle_states[1].electronic_state
        )

    def test_normalize(self):
        """
        Test the `normalize` method.
        """
        # ! add test when `ElectronicEigenvalues` is implemented
        pass


class TestAbsorptionSpectrum:
    """
    Test the `AbsorptionSpectrum` class defined in `properties/spectral_profile.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    def test_default_quantities(self):
        """
        Test the default quantities assigned when creating an instance of the `AbsorptionSpectrum` class.
        """
        absorption_spectrum = AbsorptionSpectrum()
        assert absorption_spectrum.iri == ''  # IRI is empty string by default


class TestXASSpectrum:
    """
    Test the `XASSpectrum` class defined in `properties/spectral_profile.py`.
    """

    @pytest.mark.parametrize(
        'xanes_energies, exafs_energies, xas_values',
        [
            (None, None, None),
            ([0, 1, 2], None, None),
            (None, [3, 4, 5], None),
            ([0, 1, 2], [3, 4, 5], [0.5, 0.1, 0.3, 0.2, 0.4, 0.6]),
            ([0, 1, 4], [3, 4, 5], None),
            ([0, 1, 2], [0, 4, 5], None),
        ],
    )
    def test_generate_from_contributions(
        self,
        xanes_energies: list[float] | None,
        exafs_energies: list[float] | None,
        xas_values: list[float] | None,
    ):
        """
        Test the `generate_from_contributions` method.
        """
        xas_spectrum = XASSpectrum()
        if xanes_energies is not None:
            xanes_spectrum = AbsorptionSpectrum()
            xanes_spectrum.energies = Energy(points=xanes_energies * ureg.joule)
            xanes_spectrum.value = [0.5, 0.1, 0.3]
            xas_spectrum.xanes_spectrum = xanes_spectrum
        if exafs_energies is not None:
            exafs_spectrum = AbsorptionSpectrum()
            exafs_spectrum.energies = Energy(points=exafs_energies * ureg.joule)
            exafs_spectrum.value = [0.2, 0.4, 0.6]
            xas_spectrum.exafs_spectrum = exafs_spectrum
        xas_spectrum.generate_from_contributions(logger=logger)
        if xas_spectrum.value is None:
            assert xas_values is None
        else:
            assert np.array_equal(xas_spectrum.value, xas_values)
