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
    WavefunctionConvergenceTarget,
)


class TestEnergyConvergenceTarget:
    """Test the EnergyConvergenceTarget class."""

    @pytest.mark.parametrize(
        'threshold, threshold_type, energy_values, expected_reached',
        [
            # Absolute convergence - converged
            (1e-6 * ureg.joule, 'absolute', [1e-10, 1e-11, 5e-12], True),
            # Absolute convergence - not converged
            (1e-6 * ureg.joule, 'absolute', [1e-3, 1e-4, 1e-5], False),
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
        energy_target = EnergyConvergenceTarget()
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

    def test_energy_units(self, archive, logger):
        """Test that energy convergence handles units correctly."""
        energy_target = EnergyConvergenceTarget()
        energy_target.threshold = 1e-6 * ureg.joule
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
                1e-8 * ureg.newton,
                'maximum',
                np.array([[1e-10, 2e-10, 3e-10], [1e-11, 1e-11, 1e-11]]),
                True,
            ),
            # Maximum convergence - not converged
            (
                1e-8 * ureg.newton,
                'maximum',
                np.array([[1e-5, 2e-6, 3e-6], [1e-6, 1e-7, 1e-7]]),
                False,
            ),
            # RMS convergence - converged
            (
                1e-8 * ureg.newton,
                'rms',
                np.array([[1e-10, 1e-10, 1e-10], [1e-10, 1e-10, 1e-10]]),
                True,
            ),
            # RMS convergence - not converged
            (
                1e-8 * ureg.newton,
                'rms',
                np.array([[1e-5, 1e-5, 1e-5], [1e-6, 1e-6, 1e-6]]),
                False,
            ),
            # Single atom case
            (1e-8 * ureg.newton, 'maximum', np.array([[1e-10, 1e-10, 1e-10]]), True),
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
    ):
        """
        Test force convergence with maximum and RMS types.

        Args:
            threshold: Convergence threshold value in newton.
            threshold_type: Type of convergence check ('maximum' or 'rms').
            force_values: Array of force values (n_atoms, 3).
            expected_reached: Expected value of is_reached flag.
        """
        force_target = ForceConvergenceTarget()
        force_target.threshold = threshold
        force_target.threshold_type = threshold_type

        # Create outputs with forces and scf_steps
        forces = TotalForce(value=force_values * ureg.newton)
        scf_steps = SCFSteps()  # Empty scf_steps for normalization to populate
        outputs = Outputs(total_forces=[forces], scf_steps=scf_steps)
        archive.data.outputs = [outputs]

        # Normalize outputs to compute delta_force_abs from total_forces
        outputs.normalize(archive, logger)

        # Check convergence
        is_reached = force_target.normalize(archive, logger)
        assert is_reached == expected_reached

    def test_force_absolute_convergence(self, archive, logger):
        """Test absolute force convergence from SCF delta."""
        force_target = ForceConvergenceTarget()
        force_target.threshold = 1e-8 * ureg.newton
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
            (1e-5 * ureg.joule, 'rms', np.array([1e-7, 1e-7, 1e-7, 1e-7]), True),
            # RMS convergence - not converged
            (1e-5 * ureg.joule, 'rms', np.array([1e-3, 1e-3, 1e-3, 1e-3]), False),
            # Absolute convergence - converged
            (1e-5 * ureg.joule, 'absolute', np.array([1e-8]), True),
            # Absolute convergence - not converged
            (1e-5 * ureg.joule, 'absolute', np.array([1e-3]), False),
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
    ):
        """
        Test potential convergence with RMS and absolute types.

        Args:
            threshold: Convergence threshold value in joule.
            threshold_type: Type of convergence check ('rms' or 'absolute').
            potential_values: Array of potential values.
            expected_reached: Expected value of is_reached flag.
        """
        potential_target = PotentialConvergenceTarget()
        potential_target.threshold = threshold
        potential_target.threshold_type = threshold_type

        # Create SCF steps with potential RMS values
        scf_step = SCFSteps()
        scf_step.delta_potential_rms = potential_values * ureg.joule

        archive.data.outputs = [Outputs(scf_steps=scf_step)]

        # Normalize and check
        is_reached = potential_target.normalize(archive, logger)
        assert is_reached == expected_reached


class TestChargeConvergenceTarget:
    """Test the ChargeConvergenceTarget class."""

    @pytest.mark.parametrize(
        'threshold, threshold_type, charge_values, expected_reached',
        [
            # Absolute convergence - converged
            (1e-7 * ureg.coulomb, 'absolute', np.array([1e-10, 1e-10, 1e-10]), True),
            # Absolute convergence - not converged
            (1e-7 * ureg.coulomb, 'absolute', np.array([1e-5, 1e-5, 1e-5]), False),
            # RMS convergence - converged
            (1e-7 * ureg.coulomb, 'rms', np.array([1e-10, 1e-10, 1e-10, 1e-10]), True),
            # RMS convergence - not converged
            (1e-7 * ureg.coulomb, 'rms', np.array([1e-5, 1e-5, 1e-5, 1e-5]), False),
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
    ):
        """
        Test charge convergence with absolute and RMS types.

        Args:
            threshold: Convergence threshold (dimensionless).
            threshold_type: Type of convergence check ('absolute' or 'rms').
            charge_values: Array of charge difference values.
            expected_reached: Expected value of is_reached flag.
        """
        charge_target = ChargeConvergenceTarget()
        charge_target.threshold = threshold
        charge_target.threshold_type = threshold_type

        # Create SCF steps with density RMS values (charge convergence)
        scf_step = SCFSteps()
        scf_step.delta_density_rms = charge_values * ureg.coulomb

        archive.data.outputs = [Outputs(scf_steps=scf_step)]

        # Normalize and check
        is_reached = charge_target.normalize(archive, logger)
        assert is_reached == expected_reached


class TestWavefunctionConvergenceTarget:
    """Test the WavefunctionConvergenceTarget class."""

    @pytest.mark.parametrize(
        'threshold, threshold_type, wf_values, expected_reached',
        [
            # Absolute convergence - converged
            (1e-8 * ureg.dimensionless, 'absolute', [1e-10, 1e-11, 5e-12], True),
            # Absolute convergence - not converged
            (1e-8 * ureg.dimensionless, 'absolute', [1e-5, 1e-6, 1e-7], False),
            # RMS convergence with array data - converged
            (1e-8 * ureg.dimensionless, 'rms', [[1e-10, 2e-10], [5e-11, 6e-11]], True),
            # RMS convergence with array data - not converged
            (1e-8 * ureg.dimensionless, 'rms', [[1e-5, 2e-5], [8e-6, 9e-6]], False),
            # Maximum convergence - not converged
            (
                1e-8 * ureg.dimensionless,
                'maximum',
                [[1e-7, 1e-10], [8e-7, 2e-10]],
                False,
            ),
            # Values right at threshold boundary - not converged
            (1e-8 * ureg.dimensionless, 'absolute', [0.0, 1.1e-8, 2.2e-8], False),
            # Very small values near machine epsilon
            (1e-16 * ureg.dimensionless, 'absolute', [1e-17, 5e-18, 1e-18], True),
        ],
    )
    def test_wavefunction_convergence(
        self,
        threshold: float,
        threshold_type: str,
        wf_values: list,
        expected_reached: bool,
        archive,
        logger,
    ):
        """
        Test wavefunction convergence with different thresholds and data types.

        Args:
            threshold: Convergence threshold (dimensionless).
            threshold_type: Type of convergence check.
            wf_values: List of wavefunction values (scalar or array).
            expected_reached: Expected value of is_reached flag.
        """
        wavefunction_target = WavefunctionConvergenceTarget()
        wavefunction_target.threshold = threshold
        wavefunction_target.threshold_type = threshold_type

        scf_step = SCFSteps()
        if len(wf_values) > 1:
            # Convert to deltas based on data type
            if isinstance(wf_values[0], list):
                # Array data - compute element-wise deltas
                deltas = []
                for i in range(1, len(wf_values)):
                    delta = np.abs(np.array(wf_values[i]) - np.array(wf_values[i - 1]))
                    deltas.append(delta)
                scf_step.delta_wavefunction_rms = deltas
            else:
                # Scalar data - compute simple deltas
                deltas = [
                    abs(wf_values[i] - wf_values[i - 1])
                    for i in range(1, len(wf_values))
                ]
                scf_step.delta_wavefunction_rms = np.array(deltas)

        archive.data.outputs = [Outputs(scf_steps=scf_step)]
        is_reached = wavefunction_target.normalize(archive, logger)
        assert is_reached == expected_reached


class TestMissingDataHandling:
    """Test that all convergence targets handle missing data correctly."""

    @pytest.mark.parametrize(
        'target_class, threshold, threshold_unit',
        [
            (EnergyConvergenceTarget, 1e-6, ureg.joule),
            (ForceConvergenceTarget, 1e-8, ureg.newton),
            (PotentialConvergenceTarget, 1e-5, ureg.joule),
            (ChargeConvergenceTarget, 1e-7, ureg.coulomb),
            (WavefunctionConvergenceTarget, 1e-8, ureg.dimensionless),
        ],
        ids=['Energy', 'Force', 'Potential', 'Charge', 'Wavefunction'],
    )
    def test_missing_data_returns_none(
        self, target_class, threshold, threshold_unit, archive, logger
    ):
        """Test convergence targets return None when data is missing."""
        target = target_class()
        target.threshold = threshold * threshold_unit
        target.threshold_type = 'absolute'

        # Empty archive
        is_reached = target.normalize(archive, logger)
        assert is_reached is None

        # Archive with outputs but no SCF data
        archive.data.outputs = [Outputs()]
        is_reached = target.normalize(archive, logger)
        assert is_reached is None


class TestConvergenceHelperMethods:
    """Test the base class helper methods for convergence checking."""

    def test_check_absolute(self, logger):
        """Test _check_absolute helper method."""
        energy_target = EnergyConvergenceTarget()
        # Set threshold with units
        energy_target.threshold = 1e-6 * ureg.joule

        # Test converged case
        assert energy_target._check_absolute(5e-7 * ureg.joule, logger) is True
        assert energy_target._check_absolute(-5e-7 * ureg.joule, logger) is True

        # Test not converged case
        assert energy_target._check_absolute(5e-5 * ureg.joule, logger) is False
        assert energy_target._check_absolute(-5e-5 * ureg.joule, logger) is False

        # Test boundary (now uses <=)
        assert energy_target._check_absolute(1e-6 * ureg.joule, logger) is True
        assert energy_target._check_absolute(9e-7 * ureg.joule, logger) is True

    def test_check_relative(self, logger):
        """Test _check_relative helper method."""
        energy_target = EnergyConvergenceTarget()
        # For relative convergence, threshold must be dimensionless
        # Use raw float since EnergyConvergenceTarget expects joule unit
        energy_target.threshold = 1e-6

        # Test converged case
        assert (
            energy_target._check_relative(1e-7 * ureg.joule, 1.0 * ureg.joule, logger)
            is True
        )
        assert (
            energy_target._check_relative(-1e-7 * ureg.joule, 1.0 * ureg.joule, logger)
            is True
        )

        # Test not converged case
        assert (
            energy_target._check_relative(1e-3 * ureg.joule, 1.0 * ureg.joule, logger)
            is False
        )

        # Test with different reference values
        assert (
            energy_target._check_relative(1e-6 * ureg.joule, 100.0 * ureg.joule, logger)
            is True
        )
        assert (
            energy_target._check_relative(1e-4 * ureg.joule, 100.0 * ureg.joule, logger)
            is False
        )

        # Test edge case: zero reference
        assert (
            energy_target._check_relative(0.0 * ureg.joule, 0.0 * ureg.joule, logger)
            is True
        )

    def test_check_maximum(self, logger):
        """Test _check_maximum helper method."""
        # Create a force target with units
        force_target = ForceConvergenceTarget()
        force_target.threshold = 1e-8 * ureg.newton

        # Test converged case
        values_converged = np.array([1e-10, -5e-10, 3e-10]) * ureg.newton
        assert force_target._check_maximum(values_converged, logger) is True

        # Test not converged case
        values_not_converged = np.array([1e-5, 1e-6, 1e-7]) * ureg.newton
        assert force_target._check_maximum(values_not_converged, logger) is False

        # Test multidimensional array
        values_2d = np.array([[1e-10, 2e-10], [3e-10, 4e-10]]) * ureg.newton
        assert force_target._check_maximum(values_2d, logger) is True

    def test_check_rms(self, logger):
        """Test _check_rms helper method."""
        # Create a force target with units
        force_target = ForceConvergenceTarget()
        force_target.threshold = 1e-8 * ureg.newton

        # Test converged case
        values_converged = np.array([1e-10, 1e-10, 1e-10]) * ureg.newton
        assert force_target._check_rms(values_converged, logger) is True

        # Test not converged case
        values_not_converged = np.array([1e-5, 1e-5, 1e-5]) * ureg.newton
        assert force_target._check_rms(values_not_converged, logger) is False

        # Test with zeros
        values_zero = np.array([0.0, 0.0, 0.0]) * ureg.newton
        assert force_target._check_rms(values_zero, logger) is True

        # Test multidimensional array
        values_2d = np.array([[1e-10, 2e-10], [3e-10, 4e-10]]) * ureg.newton
        rms = np.sqrt(np.mean(values_2d**2))
        assert force_target._check_rms(values_2d, logger) == (rms < 1e-8 * ureg.newton)


class TestConvergenceTypeEnumeration:
    """Test threshold_type enum validation."""

    @pytest.mark.parametrize(
        'threshold_type, threshold',
        [
            ('absolute', 1e-6 * ureg.joule),
            ('relative', 1e-6),
            ('maximum', 1e-6 * ureg.joule),
            ('rms', 1e-6 * ureg.joule),
        ],
    )
    def test_valid_convergence_types(
        self, threshold_type: str, threshold, archive, logger
    ):
        """Test that all valid convergence types are accepted."""
        energy_target = EnergyConvergenceTarget()
        energy_target.threshold_type = threshold_type
        energy_target.threshold = threshold

        # Should not raise an error
        energy_target.normalize(archive, logger)

    def test_default_convergence_type(self, archive, logger):
        """Test that default threshold_type is handled."""
        energy_target = EnergyConvergenceTarget()
        energy_target.threshold = 1e-6 * ureg.joule
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
            EnergyConvergenceTarget(
                threshold=1e-6 * ureg.joule, threshold_type='absolute'
            ),
            ForceConvergenceTarget(
                threshold=1e-8 * ureg.newton, threshold_type='maximum'
            ),
            ChargeConvergenceTarget(
                threshold=1e-7 * ureg.coulomb, threshold_type='rms'
            ),
        ]

        # Create test data
        scf_step = SCFSteps()
        scf_step.delta_energies_total = np.array([5e-7]) * ureg.joule
        scf_step.delta_density_rms = np.array([1e-8]) * ureg.coulomb

        forces = TotalForce(
            value=np.array([[1e-9, 1e-9, 1e-9], [1e-9, 1e-9, 1e-9]]) * ureg.newton
        )

        outputs = Outputs(scf_steps=scf_step, total_forces=[forces])
        archive.data.outputs = [outputs]

        # Normalize outputs to compute delta_force_abs
        outputs.normalize(archive, logger)

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
                threshold=1e-6 * ureg.joule, threshold_type='absolute'
            ),  # Will converge
            ForceConvergenceTarget(
                threshold=1e-20 * ureg.newton, threshold_type='maximum'
            ),  # Won't converge
        ]

        # Create test data
        scf_step = SCFSteps()
        scf_step.delta_energies_total = np.array([5e-7]) * ureg.joule  # Converges

        forces = TotalForce(
            value=np.array([[1e-5, 1e-5, 1e-5]]) * ureg.newton
        )  # Doesn't converge

        outputs = Outputs(scf_steps=scf_step, total_forces=[forces])
        archive.data.outputs = [outputs]

        # Normalize outputs to compute delta_force_abs
        outputs.normalize(archive, logger)

        # Normalize targets and capture results
        convergence_results = []
        for target in workflow.method.convergence_targets:
            is_reached = target.normalize(archive, logger)
            convergence_results.append(is_reached)

        assert convergence_results[0] is True
        assert convergence_results[1] is False


class TestFallbackPaths:
    """Test fallback path functionality in convergence targets."""

    def test_force_fallback_to_scf(self, archive, logger):
        """Test ForceConvergenceTarget falls back from workflow to SCF level."""
        force_target = ForceConvergenceTarget()
        force_target.threshold = 1e-8 * ureg.newton
        force_target.threshold_type = 'maximum'

        # Create SCF force data (no workflow2)
        scf_step = SCFSteps()
        scf_step.delta_force_abs = np.array([1e-9, 2e-9, 1.5e-9]) * ureg.newton

        archive.data.outputs = [Outputs(scf_steps=scf_step)]

        # Should use scf_steps.delta_force_abs since workflow2 doesn't exist
        is_reached = force_target.normalize(archive, logger)
        assert is_reached is True  # max([1e-9, 2e-9, 1.5e-9]) < 1e-8

    def test_force_fallback_to_computed(self, archive, logger):
        """Test that delta_force_abs is computed from total_forces during normalization."""
        force_target = ForceConvergenceTarget()
        force_target.threshold = 1e-8 * ureg.newton
        force_target.threshold_type = 'maximum'

        # Only provide total_forces (no workflow2, no delta_force_abs)
        forces = TotalForce(
            value=np.array([[1e-9, 1e-9, 1e-9], [2e-9, 2e-9, 2e-9]]) * ureg.newton
        )
        scf_steps = SCFSteps()  # Empty scf_steps for normalization to populate
        outputs = Outputs(total_forces=[forces], scf_steps=scf_steps)
        archive.data.outputs = [outputs]

        # Normalize outputs to compute delta_force_abs from total_forces
        outputs.normalize(archive, logger)

        # Verify delta_force_abs was computed
        assert outputs.scf_steps.delta_force_abs is not None

        # Check convergence using computed values
        is_reached = force_target.normalize(archive, logger)
        # max norm ≈ 3.46e-9 < 1e-8
        assert is_reached is True

    def test_single_path_backwards_compatible(self, archive, logger):
        """Test that single 'path' annotation still works."""
        # EnergyConvergenceTarget uses single 'path' annotation
        energy_target = EnergyConvergenceTarget()
        energy_target.threshold = 1e-6 * ureg.joule
        energy_target.threshold_type = 'absolute'

        scf_step = SCFSteps()
        scf_step.delta_energies_total = np.array([5e-7]) * ureg.joule

        archive.data.outputs = [Outputs(scf_steps=scf_step)]

        is_reached = energy_target.normalize(archive, logger)
        assert is_reached is True

    def test_energy_delta_computed_from_total_energies(self, archive, logger):
        """Test that delta_energies_total is computed from total_energies during normalization."""
        energy_target = EnergyConvergenceTarget()
        energy_target.threshold = 1e-6 * ureg.joule
        energy_target.threshold_type = 'absolute'

        # Provide total_energies but not delta_energies_total
        energies = [
            TotalEnergy(value=1.0 * ureg.joule),
            TotalEnergy(value=1.0000001 * ureg.joule),  # Delta: 1e-7
            TotalEnergy(value=1.0000002 * ureg.joule),  # Delta: 1e-7
        ]
        scf_steps = SCFSteps()  # Empty scf_steps for normalization to populate
        outputs = Outputs(total_energies=energies, scf_steps=scf_steps)
        archive.data.outputs = [outputs]

        # Normalize outputs to compute delta_energies_total
        outputs.normalize(archive, logger)

        # Verify delta_energies_total was computed
        assert outputs.scf_steps.delta_energies_total is not None
        assert len(outputs.scf_steps.delta_energies_total) == 2  # n-1 deltas

        # Check convergence using computed values
        is_reached = energy_target.normalize(archive, logger)
        # Last delta is 1e-7 < 1e-6
        assert is_reached is True


class TestThresholdTypeValidation:
    """Test threshold_type validation, especially for relative convergence."""

    def test_relative_with_dimensionless_value(self, archive, logger, caplog):
        """Test that relative convergence validation passes with dimensionless threshold."""
        import logging

        energy_target = EnergyConvergenceTarget()
        energy_target.threshold = 1e-6  # Dimensionless float
        energy_target.threshold_type = 'relative'

        scf_steps = SCFSteps(delta_energies_total=[1e-7, 5e-8] * ureg.joule)
        outputs = Outputs(scf_steps=scf_steps)
        archive.data.outputs = [outputs]

        # Validation should pass (dimensionless threshold is valid for relative)
        # But relative convergence implementation is incomplete (warns and returns None)
        with caplog.at_level(logging.WARNING):
            is_reached = energy_target.normalize(archive, logger)

        # Validation passes (no error about dimensionless requirement)
        assert (
            'Relative convergence requires dimensionless threshold' not in caplog.text
        )
        # But implementation returns None with warning
        assert is_reached is None
        assert 'Relative convergence requires reference value' in caplog.text

    def test_relative_with_pint_dimensionless(self, archive, logger, caplog):
        """Test that relative convergence validation passes with Pint dimensionless Quantity."""
        import logging

        energy_target = EnergyConvergenceTarget()
        energy_target.threshold = 1e-6 * ureg.dimensionless
        energy_target.threshold_type = 'relative'

        scf_steps = SCFSteps(delta_energies_total=[1e-7, 5e-8] * ureg.joule)
        outputs = Outputs(scf_steps=scf_steps)
        archive.data.outputs = [outputs]

        # Validation should pass (dimensionless Pint Quantity is valid for relative)
        # But relative convergence implementation is incomplete (warns and returns None)
        with caplog.at_level(logging.WARNING):
            is_reached = energy_target.normalize(archive, logger)

        # Validation passes (no error about dimensionless requirement)
        assert (
            'Relative convergence requires dimensionless threshold' not in caplog.text
        )
        # But implementation returns None with warning
        assert is_reached is None
        assert 'Relative convergence requires reference value' in caplog.text

    def test_relative_with_units_fails(self, archive, logger, caplog):
        """Test that relative convergence fails validation with dimensional units."""
        import logging

        energy_target = EnergyConvergenceTarget()
        energy_target.threshold = (
            1e-6 * ureg.joule
        )  # Has energy units - invalid for relative
        energy_target.threshold_type = 'relative'

        scf_steps = SCFSteps(delta_energies_total=[1e-7, 5e-8] * ureg.joule)
        outputs = Outputs(scf_steps=scf_steps)
        archive.data.outputs = [outputs]

        # Should fail validation and return None
        with caplog.at_level(logging.ERROR):
            is_reached = energy_target.normalize(archive, logger)

        assert is_reached is None
        # Should log error with structured data about unit mismatch
        assert '"threshold_type": "relative"' in caplog.text
        assert '"requires_physical_units": false' in caplog.text
        assert '"has_physical_units": true' in caplog.text
        # Should NOT reach the "requires reference" warning (validation fails first)
        assert 'Relative convergence requires reference value' not in caplog.text

    def test_absolute_with_units_succeeds(self, archive, logger):
        """Test that absolute convergence works fine with dimensional units."""
        energy_target = EnergyConvergenceTarget()
        energy_target.threshold = 1e-6 * ureg.joule  # Has units - valid for absolute
        energy_target.threshold_type = 'absolute'

        scf_steps = SCFSteps(delta_energies_total=[1e-7, 5e-8] * ureg.joule)
        outputs = Outputs(scf_steps=scf_steps)
        archive.data.outputs = [outputs]

        # Should validate and check convergence
        is_reached = energy_target.normalize(archive, logger)
        assert is_reached is True

    def test_maximum_with_units_succeeds(self, archive, logger):
        """Test that maximum convergence works with dimensional units."""
        force_target = ForceConvergenceTarget()
        force_target.threshold = 1e-8 * ureg.newton  # Has units - valid for maximum
        force_target.threshold_type = 'maximum'

        scf_steps = SCFSteps(
            delta_force_abs=[1e-9, 5e-10, 2e-10] * ureg.newton  # Array for maximum
        )
        outputs = Outputs(scf_steps=scf_steps)
        archive.data.outputs = [outputs]

        # Should validate and check convergence
        is_reached = force_target.normalize(archive, logger)
        assert is_reached is True

    def test_rms_with_units_succeeds(self, archive, logger):
        """Test that rms convergence works with dimensional units."""
        force_target = ForceConvergenceTarget()
        force_target.threshold = 1e-8 * ureg.newton  # Has units - valid for rms
        force_target.threshold_type = 'rms'

        scf_steps = SCFSteps(
            delta_force_abs=[1e-9, 5e-10, 2e-10] * ureg.newton  # Array for rms
        )
        outputs = Outputs(scf_steps=scf_steps)
        archive.data.outputs = [outputs]

        # Should validate and check convergence
        is_reached = force_target.normalize(archive, logger)
        assert is_reached is True
