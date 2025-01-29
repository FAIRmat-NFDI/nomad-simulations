from nomad.datamodel import EntryArchive
import nomad.utils as utils
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.properties.electronic import DOS, SemanticDOS, SpinResolvedDOS
import numpy as np
import plotly.io as pio

logger = utils.get_logger(__name__)
length = 50

archive = EntryArchive(
    data = Simulation(
        outputs = [
            DOS(
                collections = [
                    SemanticDOS(
                        energies = list(range(length)),
                        spin_channels = [
                            SpinResolvedDOS(
                                spin = 'alpha',
                                values = list(np.abs(np.random.rand(length))),
                            ),
                            SpinResolvedDOS(
                                spin = 'beta',
                                values = list(-np.abs(np.random.rand(length))),
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
)

# archive.data.normalize(archive, logger)
archive.data.outputs[0].normalize(archive, logger)
print(archive.m_to_dict())
pio.show(archive.data.outputs[0].figures[0].figure)
