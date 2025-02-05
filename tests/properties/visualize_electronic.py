import numpy as np
import plotly.io as pio

from nomad.datamodel import EntryArchive
import nomad.utils as utils
from nomad.units import ureg
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.properties.solid_state_electronics import (
    FermiRegion,
    KResolvedElectronicProperties,
    DensityOfStates,
)


logger = utils.get_logger(__name__)
no_points = 50

archive = EntryArchive(
    data=Simulation(
        outputs=[
            KResolvedElectronicProperties(
                fermi_region=FermiRegion(valence_band_maximum=1.5 * ureg.J),
                dos=DensityOfStates(
                    fermi_region=FermiRegion(valence_band_maximum=0),
                    energies=np.array(range(no_points)) * ureg.J,
                    groups=[
                        DensityOfStates.DOSGroup(
                            label=DensityOfStates.DOSGroup.DOSLabel(
                                spin='alpha',
                            ),
                            values=list(np.abs(np.random.rand(no_points))),
                        ),
                        DensityOfStates.DOSGroup(
                            label=DensityOfStates.DOSGroup.DOSLabel(
                                spin='beta',
                            ),
                            values=list(np.abs(np.random.rand(no_points))),
                        ),
                    ],
                ),
            ),
        ],
    ),
)

# archive.data.normalize(archive, logger)
archive.data.outputs[0].normalize(archive, logger)
archive.data.outputs[0].dos.normalize(archive, logger)
print(archive.m_to_dict())
pio.show(archive.data.outputs[0].dos.figures[0].figure)
