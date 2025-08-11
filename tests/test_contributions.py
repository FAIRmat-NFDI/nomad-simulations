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


def test_contribution_list_is_shallow_only(caplog):
    nested_leaf = PotentialEnergy(value=0.5 * ureg.joule)
    mid = KineticEnergy(value=1.5 * ureg.joule, contributions=[nested_leaf])  # illegal
    top = TotalEnergy(value=2.0 * ureg.joule, contributions=[mid])

    with caplog.at_level('ERROR'):
        top.normalize(EntryArchive(), logger)

    assert any('nested contributions' in rec.message.lower() for rec in caplog.records)


def test_main_section_name_is_set_from_definition():
    items = [
        TotalEnergy(value=0.0 * ureg.joule),
        KineticEnergy(value=0.0 * ureg.joule),
        PotentialEnergy(value=0.0 * ureg.joule),
        TotalForce(value=(np.zeros((2, 3)) * ureg.newton)),
        BaseForce(value=(np.zeros((2, 3)) * ureg.newton)),
    ]
    for sec in items:
        sec.normalize(EntryArchive(), logger)
        assert sec.name == sec.__class__.__name__
