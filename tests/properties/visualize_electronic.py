import json
import numpy as np
import plotly.io as pio

from nomad.client.processing import normalize_all
from nomad.datamodel import EntryArchive, EntryMetadata
import nomad.utils as utils
from nomad.units import ureg
from nomad_simulations.schema_packages.general import Simulation, ModelSystem, ModelMethod
from nomad_simulations.schema_packages.properties.solid_state_electronics import (
    FermiRegion,
    KResolvedElectronicProperties,
    DensityOfStates,
)


logger = utils.get_logger(__name__)
no_points = 50
v_dos = np.append(0, np.append(np.abs(np.random.rand(no_points-2)), 0))

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
                            values=list(v_dos),
                        ),
                        DensityOfStates.DOSGroup(
                            label=DensityOfStates.DOSGroup.DOSLabel(
                                spin='beta',
                            ),
                            values=list(-v_dos),
                        ),
                        DensityOfStates.DOSGroup(
                            label=DensityOfStates.DOSGroup.DOSLabel(
                                spin='alpha',
                                element='Fe',
                            ),
                            values=list(v_dos / 2),
                        ),
                        DensityOfStates.DOSGroup(
                            label=DensityOfStates.DOSGroup.DOSLabel(
                                spin='beta',
                                element='Fe',
                            ),
                            values=list(-v_dos / 2),
                        ),
                    ],
                ),
            ),
        ],
        model_system=[ModelSystem()],
        model_method=[ModelMethod()],
    ),
    metadata=EntryMetadata(entry_id='test'),
)

normalize_all(archive)
with open('test.archive.json', 'w') as f:
    json.dump(archive.m_to_dict(with_def_id=True), f)
# pio.show(archive.data.outputs[0].dos.figures[0].figure)
