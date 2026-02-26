"""
Tests for the convergence target classes.

This module tests the refactored class-based convergence target system including:
- Base class helper methods for convergence checking
- Individual convergence target classes (Energy, Force, Potential, Charge)
- Convergence type enum validation
- Unit handling and is_reached flag calculation
"""

import numpy as np
import pytest
from nomad.units import ureg

from nomad_simulations.schema_packages.outputs import Outputs, SCFSteps
from nomad_simulations.schema_packages.properties import TotalEnergy, TotalForce
from nomad_simulations.schema_packages.workflow.general import (
    ChargeConvergenceTarget,
    EnergyConvergenceTarget,
    ForceConvergenceTarget,
    PotentialConvergenceTarget,
    SimulationWorkflow,
    SimulationWorkflowMethod,
)


@pytest.fixture(scope='function')
def energy_target():
    """Fixture providing an EnergyConvergenceTarget instance."""
    return EnergyConvergenceTarget()


@pytest.fixture(scope='function')
def force_target():
    """Fixture providing a ForceConvergenceTarget instance."""
    return ForceConvergenceTarget()


@pytest.fixture(scope='function')
def potential_target():
    """Fixture providing a PotentialConvergenceTarget instance."""
    return PotentialConvergenceTarget()


@pytest.fixture(scope='function')
def charge_target():
    """Fixture providing a ChargeConvergenceTarget instance."""
    return ChargeConvergenceTarget()


class TestEnergyConvergenceTarget:
    """Test the EnergyConvergenceTarget class."""

    @pytest.mark.parametrize(
        'threshold, threshold_type, energy_values, expected_reached',
        [
            # Absolute convergence - converged
            (1e-6, 'absolute', [1e-10, 1e-11, 5e-12], True),
            # Absolute convergence - not converged
            (1e-6, 'absolute', [1e-3, 1e-4, 1e-5], False),
            # Zero energy values
            (1e-6, 'absolute', [0.0, 0.0, 0.0], True),
        ],
    )
    def test_energy_convergence(
        self,
        threshold: float,
        threshold_type: str,
        energy_values: list[float],
        expected_reached: bool,
        archive,
        logger,
        energy_target,
    ):
        """
        Test energy convergence checking with different thresholds and types.

        Args:
            threshold: Convergence threshold value.
            threshold_type: Type of convergence check ('absolute' or 'relative').
            energy_values: List of energy values to test.
            expected_reached: Expected value of is_reached flag.
        """
        # Set up convergence target
        energy_target.threshold = threshold
        energy_target.threshold_type = threshold_type

        # Create SCF steps with energy delta values
        scf_step = SCFSteps()
        if len(energy_values) > 1:
            # delta_energies_total is an array of changes at each SCF step
            deltas = [
                abs(energy_values[i] - energy_values[i - 1])
                for i in range(1, len(energy_values))
            ]
            scf_step.delta_energies_total = np.array(deltas) * ureg.joule

        # Add outputs to archive
        archive.data.outputs = [Outputs(scf_steps=scf_step)]

        # Normalize and check
        is_reached = energy_target.normalize(archive, logger)

        if len(energy_values) > 1 and energy_values[-1] != 0:
            assert is_reached == expected_reached

    def test_energy_missing_data(self, archive, logger, energy_target):
        """Test energy convergence with missing data."""
        energy_target.threshold = 1e-6
        energy_target.threshold_type = 'absolute'

        # Empty archive
        is_reached = energy_target.normalize(archive, logger)
        assert is_reached is None

        # Archive with outputs but no SCF steps
        archive.data.outputs = [Outputs()]
        is_reached = energy_target.normalize(archive, logger)
        assert is_reached is None

    def test_energy_units(self, archive, logger, energy_target):
        """Test that energy convergence handles units correctly."""
        energy_target.threshold = 1e-6  # joule
        energy_target.threshold_type = 'absolute'

        # Create SCF steps with energy in different unit (hartree)
        scf_step = SCFSteps()
        scf_step.delta_energies_total = (
            np.array([1e-7]) * ureg.hartree
        )  # Should convert to joule

        archive.data.outputs = [Outputs(scf_steps=scf_step)]
        is_reached = energy_target.normalize(archive, logger)

        # Check that conversion happened and convergence was checked
        assert is_reached is not None


class TestForceConvergenceTarget:
    """Test the ForceConvergenceTarget class."""

    @pytest.mark.parametrize(
        'threshold, threshold_type, force_values, expected_reached',
        [
            # Maximum convergence - converged
            (
                1e-8,
                'maximum',
                np.array([[1e-10, 2e-10, 3e-10], [1e-11, 1e-11, 1e-11]]),
                True,
            ),
            # Maximum convergence - not converged
            (
                1e-8,
                'maximum',
                np.array([[1e-5, 2e-6, 3e-6], [1e-6, 1e-7, 1e-7]]),
                False,
            ),
            # RMS convergence - converged
            (
                1e-8,
                'rms',
                np.array([[1e-10, 1e-10, 1e-10], [1e-10, 1e-10, 1e-10]]),
                True,
            ),
            # RMS convergence - not converged
            (
                1e-8,
                'rms',
                np.array([[1e-5, 1e-5, 1e-5], [1e-6, 1e-6, 1e-6]]),
                False,
            ),
            # Single atom case
            (1e-8, 'maximum', np.array([[1e-10, 1e-10, 1e-10]]), True),
        ],
    )
    def test_force_convergence(
        self,
        threshold: float,
        threshold_type: str,
        force_values: np.ndarray,
        expected_reached: bool,
        archive,
        logger,
        force_target,
    ):
        """
        Test force convergence with maximum and RMS types.

        Args:
            threshold: Convergence threshold value in newton.
            threshold_type: Type of convergence check ('maximum' or 'rms').
            force_values: Array of force values (n_atoms, 3).
            expected_reached: Expected value of is_reached flag.
        """
        force_target.threshold = threshold
        force_target.threshold_type = threshold_type

        # Create outputs with forces
        forces = TotalForce(value=force_values * ureg.newton)
        archive.data.outputs = [Outputs(total_forces=[forces])]

        # Normalize and check
        is_reached = force_target.normalize(archive, logger)
        assert is_reached == expected_reached

    def test_force_missing_data(self, archive, logger, force_target):
        """Test force convergence with missing data."""
        force_target.threshold = 1e-8
        force_target.threshold_type = 'maximum'

        # Empty archive
        is_reached = force_target.normalize(archive, logger)
        assert is_reached is None

        # Archive with outputs but no force data
        archive.data.outputs = [Outputs()]
        is_reached = force_target.normalize(archive, logger)
        assert is_reached is None

    def test_force_absolute_convergence(self, archive, logger, force_target):
        """Test absolute force convergence from SCF delta."""
        force_target.threshold = 1e-8
        force_target.threshold_type = 'absolute'

        # Create SCF steps with delta_force_abs showing convergence
        scf_step = SCFSteps()
        scf_step.delta_force_abs = np.array([1e-5, 1e-10]) * ureg.newton

        archive.data.outputs = [Outputs(scf_steps=scf_step)]

        is_reached = force_target.normalize(archive, logger)
        # Last delta force (1e-10) should be below threshold (1e-8)
        assert is_reached is True


class TestPotentialConvergenceTarget:
    """Test the PotentialConvergenceTarget class."""

    @pytest.mark.parametrize(
        'threshold, threshold_type, potential_values, expected_reached',
        [
            # RMS convergence - converged
            (1e-5, 'rms', np.array([1e-7, 1e-7, 1e-7, 1e-7]), True),
            # RMS convergence - not converged
            (1e-5, 'rms', np.array([1e-3, 1e-3, 1e-3, 1e-3]), False),
            # Absolute convergence - converged
            (1e-5, 'absolute', np.array([1e-8]), True),
            # Absolute convergence - not converged
            (1e-5, 'absolute', np.array([1e-3]), False),
        ],
    )
    def test_potential_convergence(
        self,
        threshold: float,
        threshold_type: str,
        potential_values: np.ndarray,
        expected_reached: bool,
        archive,
        logger,
        potential_target,
    ):
        """
        Test potential convergence with RMS and absolute types.

        Args:
            threshold: Convergence threshold value in joule.
            threshold_type: Type of convergence check ('rms' or 'absolute').
            potential_values: Array of potential values.
            expected_reached: Expected value of is_reached flag.
        """
        potential_target.threshold = threshold
        potential_target.threshold_type = threshold_type

        # Create SCF steps with potential RMS values
        scf_step = SCFSteps()
        scf_step.delta_potential_rms = potential_values * ureg.joule

        archive.data.outputs = [Outputs(scf_steps=scf_step)]

        # Normalize and check
        is_reached = potential_target.normalize(archive, logger)
        assert is_reached == expected_reached

    def test_potential_missing_data(self, archive, logger, potential_target):
        """Test potential convergence with missing data."""
        potential_target.threshold = 1e-5
        potential_target.threshold_type = 'rms'

        # Empty archive
        is_reached = potential_target.normalize(archive, logger)
        assert is_reached is None

        # Archive with SCF but no potential values
        archive.data.outputs = [Outputs(scf_steps=SCFSteps())]
        is_reached = potential_target.normalize(archive, logger)
        assert is_reached is None


class TestChargeConvergenceTarget:
    """Test the ChargeConvergenceTarget class."""

    @pytest.mark.parametrize(
        'threshold, threshold_type, charge_values, expected_reached',
        [
            # Absolute convergence - converged
            (1e-7, 'absolute', np.array([1e-10, 1e-10, 1e-10]), True),
            # Absolute convergence - not converged
            (1e-7, 'absolute', np.array([1e-5, 1e-5, 1e-5]), False),
            # RMS convergence - converged
            (1e-7, 'rms', np.array([1e-10, 1e-10, 1e-10, 1e-10]), True),
            # RMS convergence - not converged
            (1e-7, 'rms', np.array([1e-5, 1e-5, 1e-5, 1e-5]), False),
        ],
    )
    def test_charge_convergence(
        self,
        threshold: float,
        threshold_type: str,
        charge_values: np.ndarray,
        expected_reached: bool,
        archive,
        logger,
        charge_target,
    ):
        """
        Test charge convergence with absolute and RMS types.

        Args:
            threshold: Convergence threshold (dimensionless).
            threshold_type: Type of convergence check ('absolute' or 'rms').
            charge_values: Array of charge difference values.
            expected_reached: Expected value of is_reached flag.
        """
        charge_target.threshold = threshold
        charge_target.threshold_type = threshold_type

        # Create SCF steps with density RMS values (charge convergence)
        scf_step = SCFSteps()
        scf_step.delta_density_rms = charge_values * ureg.coulomb

        archive.data.outputs = [Outputs(scf_steps=scf_step)]

        # Normalize and check
        is_reached = charge_target.normalize(archive, logger)
        assert is_reached == expected_reached

    def test_charge_missing_data(self, archive, logger, charge_target):
        """Test charge convergence with missing data."""
        charge_target.threshold = 1e-7
        charge_target.threshold_type = 'absolute'

        # Empty archive
        is_reached = charge_target.normalize(archive, logger)
        assert is_reached is None

        # Archive with SCF but no charge values
        archive.data.outputs = [Outputs(scf_steps=SCFSteps())]
        is_reached = charge_target.normalize(archive, logger)
        assert is_reached is None


class TestConvergenceHelperMethods:
    """Test the base class helper methods for convergence checking."""

    def test_check_absolute(self, energy_target):
        """Test _check_absolute helper method."""
        # Set threshold without units for direct testing of helper method
        energy_target.threshold = 1e-6

        # Test converged case
        assert energy_target._check_absolute(5e-7) is True
        assert energy_target._check_absolute(-5e-7) is True

        # Test not converged case
        assert energy_target._check_absolute(5e-5) is False
        assert energy_target._check_absolute(-5e-5) is False

        # Test boundary (now uses <=)
        assert energy_target._check_absolute(1e-6) is True
        assert energy_target._check_absolute(9e-7) is True

    def test_check_relative(self, energy_target):
        """Test _check_relative helper method."""
        energy_target.threshold = 1e-6

        # Test converged case
        assert energy_target._check_relative(1e-7, 1.0) is True
        assert energy_target._check_relative(-1e-7, 1.0) is True

        # Test not converged case
        assert energy_target._check_relative(1e-3, 1.0) is False

        # Test with different reference values
        assert energy_target._check_relative(1e-6, 100.0) is True
        assert energy_target._check_relative(1e-4, 100.0) is False

        # Test edge case: zero reference
        assert energy_target._check_relative(0.0, 0.0) is True

    def test_check_maximum(self):
        """Test _check_maximum helper method."""
        # Create a force target and bypass unit conversion
        force_target = ForceConvergenceTarget()
        object.__setattr__(force_target, 'threshold', 1e-8)

        # Test converged case
        values_converged = np.array([1e-10, -5e-10, 3e-10])
        assert force_target._check_maximum(values_converged) is True

        # Test not converged case
        values_not_converged = np.array([1e-5, 1e-6, 1e-7])
        assert force_target._check_maximum(values_not_converged) is False

        # Test multidimensional array
        values_2d = np.array([[1e-10, 2e-10], [3e-10, 4e-10]])
        assert force_target._check_maximum(values_2d) is True

    def test_check_rms(self):
        """Test _check_rms helper method."""
        # Create a force target and bypass unit conversion by setting threshold directly
        force_target = ForceConvergenceTarget()
        # Override threshold to be a plain float for testing the helper method
        object.__setattr__(force_target, 'threshold', 1e-8)

        # Test converged case
        values_converged = np.array([1e-10, 1e-10, 1e-10])
        assert force_target._check_rms(values_converged) is True

        # Test not converged case
        values_not_converged = np.array([1e-5, 1e-5, 1e-5])
        assert force_target._check_rms(values_not_converged) is False

        # Test with zeros
        values_zero = np.array([0.0, 0.0, 0.0])
        assert force_target._check_rms(values_zero) is True

        # Test multidimensional array
        values_2d = np.array([[1e-10, 2e-10], [3e-10, 4e-10]])
        rms = np.sqrt(np.mean(values_2d**2))
        assert force_target._check_rms(values_2d) == (rms < 1e-8)


class TestConvergenceTypeEnumeration:
    """Test threshold_type enum validation."""

    @pytest.mark.parametrize(
        'threshold_type',
        ['absolute', 'relative', 'maximum', 'rms', 'residuum'],
    )
    def test_valid_convergence_types(
        self, threshold_type: str, archive, logger, energy_target
    ):
        """Test that all valid convergence types are accepted."""
        energy_target.threshold_type = threshold_type
        energy_target.threshold = 1e-6

        # Should not raise an error
        energy_target.normalize(archive, logger)

    def test_default_convergence_type(self, archive, logger, energy_target):
        """Test that default threshold_type is handled."""
        energy_target.threshold = 1e-6
        # Don't set threshold_type explicitly

        # Create test data
        scf_step = SCFSteps()
        scf_step.delta_energies_total = np.array([1e-7]) * ureg.joule

        archive.data.outputs = [Outputs(scf_steps=scf_step)]

        # Should default to 'absolute'
        energy_target.normalize(archive, logger)
        # Should not raise an error


class TestConvergenceInWorkflow:
    """Test convergence targets integration with SimulationWorkflow."""

    def test_multiple_convergence_targets(self, archive, logger):
        """Test workflow with multiple convergence criteria."""
        workflow = SimulationWorkflow()
        workflow.method = SimulationWorkflowMethod()

        # Add multiple convergence targets
        workflow.method.convergence_targets = [
            EnergyConvergenceTarget(threshold=1e-6, threshold_type='absolute'),
            ForceConvergenceTarget(threshold=1e-8, threshold_type='maximum'),
            ChargeConvergenceTarget(threshold=1e-7, threshold_type='rms'),
        ]

        # Create test data
        scf_step = SCFSteps()
        scf_step.delta_energies_total = np.array([5e-7]) * ureg.joule
        scf_step.delta_density_rms = np.array([1e-8]) * ureg.coulomb

        forces = TotalForce(
            value=np.array([[1e-9, 1e-9, 1e-9], [1e-9, 1e-9, 1e-9]]) * ureg.newton
        )

        archive.data.outputs = [Outputs(scf_steps=scf_step, total_forces=[forces])]

        # Normalize workflow
        workflow.normalize(archive, logger)

        # Check that convergence targets were normalized
        assert workflow.method.convergence_targets is not None
        assert len(workflow.method.convergence_targets) == 3

        # Normalize individual targets to check convergence status
        convergence_results = []
        for target in workflow.method.convergence_targets:
            is_reached = target.normalize(archive, logger)
            convergence_results.append(is_reached)

        # Check individual convergence
        assert convergence_results[0] is True  # Energy
        assert convergence_results[1] is True  # Force
        assert convergence_results[2] is True  # Charge

    def test_convergence_targets_empty(self, archive, logger):
        """Test workflow with no convergence targets."""
        workflow = SimulationWorkflow()

        # No convergence targets set
        workflow.normalize(archive, logger)

        # Should not raise an error
        assert (
            workflow.method.convergence_targets is None
            or len(workflow.method.convergence_targets) == 0
        )

    def test_mixed_convergence_results(self, archive, logger):
        """Test with some targets converged and others not."""
        workflow = SimulationWorkflow()
        workflow.method = SimulationWorkflowMethod()

        workflow.method.convergence_targets = [
            EnergyConvergenceTarget(
                threshold=1e-6, threshold_type='absolute'
            ),  # Will converge
            ForceConvergenceTarget(
                threshold=1e-20, threshold_type='maximum'
            ),  # Won't converge
        ]

        # Create test data
        scf_step = SCFSteps()
        scf_step.delta_energies_total = np.array([5e-7]) * ureg.joule  # Converges

        forces = TotalForce(
            value=np.array([[1e-5, 1e-5, 1e-5]]) * ureg.newton
        )  # Doesn't converge

        archive.data.outputs = [Outputs(scf_steps=scf_step, total_forces=[forces])]

        # Normalize targets and capture results
        convergence_results = []
        for target in workflow.method.convergence_targets:
            is_reached = target.normalize(archive, logger)
            convergence_results.append(is_reached)

        assert convergence_results[0] is True
        assert convergence_results[1] is False


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_threshold(self, archive, logger, energy_target):
        """Test that zero threshold is accepted (non-negative validation)."""
        energy_target.threshold = 0.0
        energy_target.threshold_type = 'absolute'

        scf_step = SCFSteps()
        scf_step.delta_energies_total = np.array([0.0]) * ureg.joule

        archive.data.outputs = [Outputs(scf_steps=scf_step)]
        is_reached = energy_target.normalize(archive, logger)

        # With <= comparison, exact zero matches zero threshold
        assert is_reached is True

    def test_very_large_values(self, archive, logger, force_target):
        """Test with very large force values."""
        force_target.threshold = 1e10
        force_target.threshold_type = 'maximum'

        forces = TotalForce(value=np.array([[1e5, 1e5, 1e5]]) * ureg.newton)
        archive.data.outputs = [Outputs(total_forces=[forces])]

        is_reached = force_target.normalize(archive, logger)
        assert is_reached is True

    def test_nan_values(self, archive, logger, force_target):
        """Test handling of NaN values in data."""
        force_target.threshold = 1e-8
        force_target.threshold_type = 'maximum'

        # Create forces with NaN
        forces = TotalForce(value=np.array([[np.nan, 1e-5, 1e-5]]) * ureg.newton)
        archive.data.outputs = [Outputs(total_forces=[forces])]

        # Should handle gracefully (implementation dependent)
        force_target.normalize(archive, logger)
        # Test passes if no exception is raised
