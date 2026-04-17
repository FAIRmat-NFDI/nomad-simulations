import numpy as np
import pytest

from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.workflow.molecular_dynamics import (
    BarostatParameters,
    FreeEnergyCalculationParameters,
    Lambdas,
    MolecularDynamics,
    MolecularDynamicsMethod,
    MolecularDynamicsResults,
    ShearParameters,
    ThermostatParameters,
)


@pytest.fixture
def thermostat_parameters():
    return ThermostatParameters()


@pytest.fixture
def barostat_parameters():
    return BarostatParameters()


@pytest.fixture
def shear_parameters():
    return ShearParameters()


@pytest.fixture
def lambdas():
    return Lambdas()


@pytest.fixture
def free_energy_parameters():
    return FreeEnergyCalculationParameters()


@pytest.fixture
def md_method():
    return MolecularDynamicsMethod()


class TestThermostatParameters:
    def test_default_initialization(self, thermostat_parameters):
        assert thermostat_parameters.thermostat_type is None
        assert thermostat_parameters.reference_temperature is None
        assert thermostat_parameters.coupling_constant is None

    @pytest.mark.parametrize(
        'thermostat_type',
        [
            'andersen',
            'berendsen',
            'nose_hoover',
            'velocity_rescaling',
            'langevin_goga',
        ],
    )
    def test_thermostat_types(self, thermostat_parameters, thermostat_type):
        thermostat_parameters.thermostat_type = thermostat_type
        assert thermostat_parameters.thermostat_type == thermostat_type

    @pytest.mark.parametrize('temp_profile', ['constant', 'linear', 'exponential'])
    def test_temperature_profiles(self, thermostat_parameters, temp_profile):
        thermostat_parameters.temperature_profile = temp_profile
        assert thermostat_parameters.temperature_profile == temp_profile

    def test_reference_temperature(self, thermostat_parameters):
        thermostat_parameters.reference_temperature = 300.0
        assert thermostat_parameters.reference_temperature.magnitude == 300.0


class TestBarostatParameters:
    def test_default_initialization(self, barostat_parameters):
        assert barostat_parameters.barostat_type is None
        assert barostat_parameters.coupling_type is None
        assert barostat_parameters.reference_pressure is None

    @pytest.mark.parametrize(
        'barostat_type',
        [
            'berendsen',
            'nose_hoover',
            'parrinello_rahman',
            'martyna_tuckerman_tobias_klein',
            'stochastic_cell_rescaling',
        ],
    )
    def test_barostat_types(self, barostat_parameters, barostat_type):
        barostat_parameters.barostat_type = barostat_type
        assert barostat_parameters.barostat_type == barostat_type

    @pytest.mark.parametrize(
        'coupling_type', ['isotropic', 'semi_isotropic', 'anisotropic']
    )
    def test_coupling_types(self, barostat_parameters, coupling_type):
        barostat_parameters.coupling_type = coupling_type
        assert barostat_parameters.coupling_type == coupling_type

    def test_reference_pressure_matrix(self, barostat_parameters):
        pressure_matrix = np.eye(3) * 1e5  # 1 bar in Pa
        barostat_parameters.reference_pressure = pressure_matrix
        assert np.array_equal(
            barostat_parameters.reference_pressure.magnitude, pressure_matrix
        )


class TestShearParameters:
    def test_default_initialization(self, shear_parameters):
        assert shear_parameters.shear_type is None
        assert shear_parameters.shear_rate is None

    @pytest.mark.parametrize(
        'shear_type', ['lees_edwards', 'trozzi_ciccotti', 'ashurst_hoover']
    )
    def test_shear_types(self, shear_parameters, shear_type):
        shear_parameters.shear_type = shear_type
        assert shear_parameters.shear_type == shear_type

    def test_shear_rate_matrix(self, shear_parameters):
        shear_rate_matrix = np.zeros((3, 3))
        shear_rate_matrix[0, 1] = 0.01  # τ_yx component
        shear_parameters.shear_rate = shear_rate_matrix
        assert np.array_equal(shear_parameters.shear_rate.magnitude, shear_rate_matrix)


class TestLambdas:
    def test_default_initialization(self, lambdas):
        assert lambdas.interaction_type is None
        assert lambdas.lambda_values is None
        assert lambdas.endpoints_on is None

    @pytest.mark.parametrize(
        'interaction_type',
        ['output', 'coulomb', 'vdw', 'bonded', 'restraint', 'mass', 'temperature'],
    )
    def test_interaction_types(self, lambdas, interaction_type):
        lambdas.interaction_type = interaction_type
        assert lambdas.interaction_type == interaction_type

    def test_lambda_grid(self, lambdas, archive, logger):
        lambda_values = np.linspace(0.0, 1.0, 11)
        lambdas.lambda_values = lambda_values
        lambdas.normalize(archive, logger)
        assert np.array_equal(lambdas.lambda_values, lambda_values)

    def test_non_monotonic_warning(self, lambdas, archive, logger):
        lambdas.lambda_values = np.array([0.0, 0.5, 0.3, 1.0])
        lambdas.normalize(archive, logger)
        assert len(lambdas.lambda_values) == 4

    def test_softcore_parameters(self, lambdas):
        lambdas.interaction_type = 'vdw'
        lambdas.softcore_enabled = True
        lambdas.softcore_alpha = 0.5
        lambdas.softcore_p = 1
        lambdas.softcore_sigma = 0.3
        assert lambdas.softcore_enabled is True
        assert lambdas.softcore_alpha == 0.5
        assert lambdas.softcore_p == 1
        assert lambdas.softcore_sigma == 0.3


class TestFreeEnergyCalculationParameters:
    def test_default_initialization(self, free_energy_parameters):
        assert free_energy_parameters.calc_type is None
        assert free_energy_parameters.lambdas == []

    @pytest.mark.parametrize('calc_type', ['alchemical', 'umbrella_sampling'])
    def test_calc_types(self, free_energy_parameters, calc_type):
        free_energy_parameters.calc_type = calc_type
        assert free_energy_parameters.calc_type == calc_type

    def test_multiple_lambda_dimensions(self, free_energy_parameters, logger, archive):
        # Create lambda schedules for vdw and coulomb
        lambda_vdw = Lambdas(
            interaction_type='vdw', lambda_values=np.linspace(0.0, 1.0, 11)
        )
        lambda_coul = Lambdas(
            interaction_type='coulomb', lambda_values=np.linspace(0.0, 1.0, 11)
        )
        free_energy_parameters.lambdas = [lambda_vdw, lambda_coul]
        free_energy_parameters.normalize(archive, logger)
        assert len(free_energy_parameters.lambdas) == 2

    def test_range_check_outside_bounds(self, free_energy_parameters, archive, logger):
        free_energy_parameters.calc_type = 'alchemical'
        lam = Lambdas(interaction_type='vdw', lambda_values=np.array([0.0, 0.5, 1.5]))
        free_energy_parameters.lambdas.append(lam)
        free_energy_parameters.normalize(archive, logger)
        # Values outside [0,1] — normalize should warn but not raise

    def test_current_lambda_index_in_bounds(
        self, free_energy_parameters, archive, logger
    ):
        lam = Lambdas(
            interaction_type='output',
            lambda_values=np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0]),
        )
        free_energy_parameters.lambdas.append(lam)
        free_energy_parameters.current_lambda_index = 3
        free_energy_parameters.normalize(archive, logger)
        assert free_energy_parameters.current_lambda_index == 3

    def test_current_lambda_index_out_of_bounds(
        self, free_energy_parameters, archive, logger
    ):
        lam = Lambdas(
            interaction_type='output', lambda_values=np.array([0.0, 0.5, 1.0])
        )
        free_energy_parameters.lambdas.append(lam)
        free_energy_parameters.current_lambda_index = 10
        free_energy_parameters.normalize(archive, logger)
        # Out-of-bounds index is clamped to grid_len - 1, not cleared
        assert free_energy_parameters.current_lambda_index == 2


class TestMolecularDynamicsMethod:
    def test_default_initialization(self, md_method):
        assert md_method.thermodynamic_ensemble is None
        assert md_method.integrator_type is None
        assert md_method.integration_timestep is None

    @pytest.mark.parametrize('ensemble', ['NVE', 'NVT', 'NPT', 'NPH'])
    def test_thermodynamic_ensembles(self, md_method, ensemble):
        md_method.thermodynamic_ensemble = ensemble
        assert md_method.thermodynamic_ensemble == ensemble

    @pytest.mark.parametrize(
        'integrator',
        [
            'leap_frog',
            'velocity_verlet',
            'langevin_leap_frog',
            'rRESPA_multitimescale',
        ],
    )
    def test_integrator_types(self, md_method, integrator):
        md_method.integrator_type = integrator
        assert md_method.integrator_type == integrator

    def test_timestep_and_steps(self, md_method):
        md_method.integration_timestep = 2e-15  # 2 fs
        md_method.n_steps = 1000000
        assert md_method.integration_timestep.magnitude == 2e-15
        assert md_method.n_steps == 1000000

    def test_thermostat_attachment(self, md_method):
        thermostat = ThermostatParameters(
            thermostat_type='nose_hoover', reference_temperature=300.0
        )
        md_method.thermostat_parameters = [thermostat]
        assert len(md_method.thermostat_parameters) == 1
        assert md_method.thermostat_parameters[0].thermostat_type == 'nose_hoover'

    def test_barostat_attachment(self, md_method):
        barostat = BarostatParameters(
            barostat_type='parrinello_rahman',
            coupling_type='isotropic',
        )
        md_method.barostat_parameters = [barostat]
        assert len(md_method.barostat_parameters) == 1
        assert md_method.barostat_parameters[0].barostat_type == 'parrinello_rahman'

    def test_multiple_thermostats(self, md_method):
        # Test multiple thermostats for different frame ranges
        thermostat1 = ThermostatParameters(
            thermostat_type='berendsen',
            reference_temperature=300.0,
            frame_start=0,
            frame_end=1000,
        )
        thermostat2 = ThermostatParameters(
            thermostat_type='nose_hoover',
            reference_temperature=350.0,
            frame_start=1000,
            frame_end=2000,
        )
        md_method.thermostat_parameters = [thermostat1, thermostat2]
        assert len(md_method.thermostat_parameters) == 2


class TestMolecularDynamics:
    n_outputs = 3

    def test_inputs_outputs(self, logger, archive):
        archive.data.outputs = [Outputs() for _ in range(self.n_outputs)]
        workflow = MolecularDynamics()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.method, MolecularDynamicsMethod)
        assert isinstance(workflow.results, MolecularDynamicsResults)
        assert len(workflow.tasks) == self.n_outputs
        for n, task in enumerate(workflow.tasks):
            assert task.name == f'Step {n}'

    def test_method_initialization(self, logger, archive):
        workflow = MolecularDynamics()
        workflow.normalize(archive, logger)
        assert workflow.method is not None
        assert isinstance(workflow.method, MolecularDynamicsMethod)

    def test_results_initialization(self, logger, archive):
        workflow = MolecularDynamics()
        workflow.normalize(archive, logger)
        assert workflow.results is not None
        assert isinstance(workflow.results, MolecularDynamicsResults)

    def test_prevents_duplicate_observables_on_renormalization(self, logger, archive):
        """Test that re-running normalize() doesn't duplicate RDF/MSD calculations."""
        # Create a workflow and add some mock observables to simulate first normalization
        workflow = MolecularDynamics()
        # Pre-populate observables as if they were calculated
        from nomad_simulations.schema_packages.properties import (
            RadialDistributionFunction,
        )

        mock_rdf = RadialDistributionFunction()
        workflow.radial_distribution_functions = [mock_rdf]

        # Store initial counts
        initial_rdf_count = len(workflow.radial_distribution_functions)

        # Re-run normalization
        workflow.normalize(archive, logger)
        final_rdf_count = len(workflow.radial_distribution_functions)

        # Assert that observables were not duplicated
        assert initial_rdf_count == final_rdf_count, (
            f'RDFs were duplicated: initial={initial_rdf_count}, final={final_rdf_count}'
        )
