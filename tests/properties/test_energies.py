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

from . import logger


def test_energy_names_and_units_via_values():
    kin = KineticEnergy(value=1.23 * ureg.joule)
    pot = PotentialEnergy(value=4.56 * ureg.joule)
    tot = TotalEnergy(value=5.79 * ureg.joule)

    for sec in (kin, pot, tot):
        sec.normalize(EntryArchive(), logger)
        assert sec.name == sec.__class__.__name__
        assert hasattr(sec.value, 'magnitude')
        _ = sec.value.to('joule')
        assert np.isfinite(sec.value.magnitude)


def test_total_energy_contributions_basic_flow_and_idempotency():
    kin = KineticEnergy(value=2.0 * ureg.joule)
    pot = PotentialEnergy(value=3.0 * ureg.joule)

    tot = TotalEnergy(value=5.0 * ureg.joule)
    tot.contributions = [kin, pot]

    assert not tot.m_cache.get('_is_normalized', False)

    tot.normalize(EntryArchive(), logger)
    assert tot.m_cache.get('_is_normalized', False)
    assert len(tot.contributions) == 2

    assert kin._is_contribution() is True
    assert pot._is_contribution() is True
    assert tot._is_contribution() is False

    figures_before = len(tot.figures)
    tot.normalize(EntryArchive(), logger)
    assert len(tot.figures) == figures_before


def test_total_energy_accepts_baseenergy_contributions_mixed():
    """
    TotalEnergy.contributions accepts BaseEnergy directly, and mixed subclasses.
    """
    gen = BaseEnergy(value=1.0 * ureg.joule, contribution_type='generic')
    kin = KineticEnergy(value=2.0 * ureg.joule)  # subclass of BaseEnergy
    pot = PotentialEnergy(value=3.0 * ureg.joule)  # subclass of BaseEnergy

    tot = TotalEnergy(value=6.0 * ureg.joule)
    tot.contributions = [gen, kin, pot]

    tot.normalize(EntryArchive(), logger)

    # Top-level is not a contribution; children are.
    assert tot._is_contribution() is False
    assert all(c._is_contribution() for c in tot.contributions)

    # Names and units behave as expected
    assert gen.name == 'BaseEnergy'
    for c in tot.contributions:
        _ = c.value.to('joule')
