from nomad_simulations.schema_packages.model_method import DFT
from nomad_simulations.schema_packages.numerical_settings import SelfConsistency


def build_model_method_overview_example() -> DFT:
    """Create a minimal DFT method section with SCF settings."""
    scf = SelfConsistency(n_max_iterations=80)
    method = DFT(
        name='DFT',
        type='KS',
        jacobs_ladder='GGA',
        numerical_settings=[scf],
    )
    return method
