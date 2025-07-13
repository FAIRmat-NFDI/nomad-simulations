from nomad_simulations.schema_packages.properties import (
    KineticEnergy,
    PotentialEnergy,
    TotalEnergy,
)


class TestTotalEnergy:
    """
    Test the `TotalEnergy` class defined in `properties/energies.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    def test_default_quantities(self):
        """
        Test the default quantities assigned when creating an instance of the `TotalEnergy` class.
        """
        total_energy = TotalEnergy()
        # assert total_energy.iri == 'http://fairmat-nfdi.eu/taxonomy/TotalEnergy'
        assert total_energy.name == 'TotalEnergy'


class TestKineticEnergy:
    """
    Test the `KineticEnergy` class defined in `properties/energies.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    def test_default_quantities(self):
        """
        Test the default quantities assigned when creating an instance of the `KineticEnergy` class.
        """
        kinetic_energy = KineticEnergy()
        # assert kinetic_energy.iri == 'http://fairmat-nfdi.eu/taxonomy/KineticEnergy'
        assert kinetic_energy.name == 'KineticEnergy'


class TestPotentialEnergy:
    """
    Test the `PotentialEnergy` class defined in `properties/energies.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    def test_default_quantities(self):
        """
        Test the default quantities assigned when creating an instance of the `PotentialEnergy` class.
        """
        potential_energy = PotentialEnergy()
        # assert potential_energy.iri == 'http://fairmat-nfdi.eu/taxonomy/PotentialEnergy'
        assert potential_energy.name == 'PotentialEnergy'
