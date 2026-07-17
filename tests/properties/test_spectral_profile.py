import numpy as np
import pytest
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.model_system import ModelSystem, Representation
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties import (
    AbsorptionSpectrum,
    DOSProfile,
    ElectronicDensityOfStates,
    XASSpectrum,
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

    def test_resolve_energies_origin(self):
        """
        Test the `resolve_energies_origin` method with a synthetic gapped DOS.

        The DOS grid runs from -0.5 to 0.5 eV in steps of 0.01 eV, with a valence band
        below -0.2 eV and a conduction band above 0.3 eV. With the Fermi level inside
        the gap, the HOMO/LUMO stored in `m_cache` are the gap-side grid points
        adjacent to the band edges.
        """
        # ! extend to the `ElectronicEigenvalues` sibling path once it is implemented
        electronic_dos = ElectronicDensityOfStates()
        energies_points = np.linspace(-0.5, 0.5, 101) * ureg.eV
        dos_values = np.zeros(101)
        dos_values[:31] = 1.0  # valence band: E <= -0.20 eV
        dos_values[80:] = 1.0  # conduction band: E >= 0.30 eV
        electronic_dos.value = dos_values * ureg('1/joule')

        energies_origin = electronic_dos.resolve_energies_origin(
            energies_points=energies_points,
            fermi_level=0.0 * ureg.eV,
            logger=logger,
        )

        homo = electronic_dos.m_cache.get('highest_occupied_energy')
        lumo = electronic_dos.m_cache.get('lowest_unoccupied_energy')
        assert np.isclose(homo.to('eV').magnitude, -0.19)
        assert np.isclose(lumo.to('eV').magnitude, 0.29)
        assert energies_origin == homo

        # The cached energies produce a finite DOS-derived band gap
        band_gap = electronic_dos.extract_band_gap()
        assert band_gap is not None
        assert np.isclose(band_gap.value.to('eV').magnitude, 0.48)

    def test_resolve_energies_origin_metallic(self):
        """
        Test `resolve_energies_origin` with a DOS that is finite across the Fermi
        level: HOMO and LUMO both resolve to the Fermi energy and the derived band
        gap is 0 (regression test: HOMO/LUMO of exactly 0 eV must not be discarded
        by the truthiness check in `extract_band_gap`).
        """
        electronic_dos = ElectronicDensityOfStates()
        energies_points = np.linspace(-0.5, 0.5, 101) * ureg.eV
        electronic_dos.value = np.ones(101) * ureg('1/joule')

        energies_origin = electronic_dos.resolve_energies_origin(
            energies_points=energies_points,
            fermi_level=0.0 * ureg.eV,
            logger=logger,
        )

        homo = electronic_dos.m_cache.get('highest_occupied_energy')
        lumo = electronic_dos.m_cache.get('lowest_unoccupied_energy')
        assert np.isclose(homo.to('eV').magnitude, 0.0, atol=1e-12)
        assert np.isclose(lumo.to('eV').magnitude, 0.0, atol=1e-12)
        assert energies_origin == homo

        band_gap = electronic_dos.extract_band_gap()
        assert band_gap is not None
        assert np.isclose(band_gap.value.to('eV').magnitude, 0.0, atol=1e-12)

    def test_resolve_energies_origin_no_reference(self):
        """
        Test that `resolve_energies_origin` returns `None` when neither an
        `ElectronicEigenvalues` sibling nor a Fermi level is available.
        """
        electronic_dos = ElectronicDensityOfStates()
        energies_points = np.linspace(-0.5, 0.5, 101) * ureg.eV
        electronic_dos.value = np.ones(101) * ureg('1/joule')

        energies_origin = electronic_dos.resolve_energies_origin(
            energies_points=energies_points,
            fermi_level=None,
            logger=logger,
        )
        assert energies_origin is None

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
