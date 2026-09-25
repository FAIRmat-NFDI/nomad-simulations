import numpy as np
from nomad import utils
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.outputs import Outputs, SCFSteps

logger = utils.get_logger(__name__)

# Pattern based on tests/workflow/test_convergence_targets.py.
outputs = Outputs(scf_steps=SCFSteps(energies_total=[1.0, 1.5, 2.1] * ureg.eV))

outputs.normalize(EntryArchive(), logger)

assert outputs.scf_steps is not None
assert outputs.scf_steps.delta_energies_total is not None
assert len(outputs.scf_steps.delta_energies_total) == 2
expected_first = (0.5 * ureg.eV).to('joule').magnitude
assert np.isclose(
    outputs.scf_steps.delta_energies_total[0].to('joule').magnitude, expected_first
)
