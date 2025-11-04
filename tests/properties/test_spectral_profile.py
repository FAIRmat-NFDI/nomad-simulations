from typing import Optional

import numpy as np
import pytest
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.model_system import AtomicCell, ModelSystem
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties import (
    AbsorptionSpectrum,
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
        Test the `resolve_energies_origin` method.
        """
        # ! add test when `ElectronicEigenvalues` is implemented
        pass

    def test_resolve_normalization_factor(self, simulation_electronic_dos: Simulation):
        """
        Test the `resolve_normalization_factor` method.
        """
        simulation = Simulation()
        outputs = Outputs()
        # We only used the `simulation_electronic_dos` fixture to get the `ElectronicDensityOfStates` to test missing refs
        electronic_dos = simulation_electronic_dos.outputs[0].electronic_dos[0]
        electronic_dos.energies_origin = 0.5 * ureg.joule
        outputs.electronic_dos.append(electronic_dos)
        simulation.outputs.append(outputs)

        # No `model_system_ref`
        assert electronic_dos.resolve_normalization_factor(logger=logger) is None

        # No `model_system_ref.cell`
        model_system = ModelSystem()
        simulation.model_system.append(model_system)
        outputs.model_system_ref = simulation.model_system[0]
        assert electronic_dos.resolve_normalization_factor(logger=logger) is None

        # model_system_ref has a cell but no particle_states
        atomic_cell = AtomicCell(type='original')
        model_system.cell.append(atomic_cell)
        # Do not set particle_states (or leave it empty)
        assert electronic_dos.resolve_normalization_factor(logger=logger) is None

        # add required particle_states into the ModelSystem
        particle_states = [AtomsState() for _ in range(2)]
        # We now manually set the atomic numbers for testing
        particle_states[0].__dict__['atomic_number'] = 31  # Ga
        particle_states[1].__dict__['atomic_number'] = 33  # As
        # Set the parent ModelSystem’s particle_states
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

    def test_extract_band_gap(self):
        """
        Test the `extract_band_gap` method.
        """
        # ! add test when `ElectronicEigenvalues` is implemented
        pass

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
            == outputs.model_system_ref.particle_states[0].orbitals_state[0]
        )
        assert (
            orbital_projected[1].entity_ref
            == outputs.model_system_ref.particle_states[1].orbitals_state[0]
        )
        # For the third orbital, assume it comes from the second particle as well (e.g. As atom has two orbitals)
        assert (
            orbital_projected[2].entity_ref
            == outputs.model_system_ref.particle_states[1].orbitals_state[1]
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
        # Check that the entity_ref of the atom PDOS corresponds to the particle state in the referenced ModelSystem
        assert (
            atom_projected[0].entity_ref == outputs.model_system_ref.particle_states[0]
        )
        assert (
            atom_projected[1].entity_ref == outputs.model_system_ref.particle_states[1]
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
