import numpy as np
import pytest
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties.energies import (
    BaseEnergy,
    KineticEnergy,
    PotentialEnergy,
    TotalEnergy,
)
from nomad_simulations.schema_packages.properties.forces import BaseForce, TotalForce

from . import logger


def test_is_contribution_detection_across_types():
    # Energies
    kin = KineticEnergy(value=1.0 * ureg.joule)
    pot = PotentialEnergy(value=2.0 * ureg.joule)
    totE = TotalEnergy(value=3.0 * ureg.joule, contributions=[kin, pot])

    # Forces
    n = 4
    f1 = BaseForce(value=(np.zeros((n, 3)) * ureg.newton))
    f2 = BaseForce(value=(np.ones((n, 3)) * ureg.newton))
    totF = TotalForce(value=(np.zeros((n, 3)) * ureg.newton), contributions=[f1, f2])

    for sec in (totE, totF):
        sec.normalize(EntryArchive(), logger)

    assert totE._is_contribution() is False
    assert kin._is_contribution() is True
    assert pot._is_contribution() is True

    assert totF._is_contribution() is False
    assert f1._is_contribution() is True
    assert f2._is_contribution() is True
