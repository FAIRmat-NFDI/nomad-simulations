import numpy as np
import pytest
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.properties.forces import BaseForce, TotalForce

from . import logger


def test_force_units_and_shapes_via_values():
    n_atoms = 5
    f_component = BaseForce(value=(np.zeros((n_atoms, 3)) * ureg.newton))
    f_total = TotalForce(value=(np.ones((n_atoms, 3)) * ureg.newton))

    for sec in (f_component, f_total):
        sec.normalize(EntryArchive(), logger)
        assert sec.name == sec.__class__.__name__
        assert hasattr(sec.value, 'magnitude')
        _ = sec.value.to('newton')
        assert sec.value.magnitude.shape == (n_atoms, 3)

    f_component_2 = BaseForce(value=(np.zeros((n_atoms, 6)) * ureg.newton))
    f_component_2.normalize(EntryArchive(), logger)
    assert f_component_2.value.magnitude.shape == (n_atoms, 6)


def test_total_force_with_multiple_contributions_idempotency_and_flags():
    n_atoms = 3
    contribs = [
        BaseForce(
            value=(np.full((n_atoms, 3), 1.0) * ureg.newton), contribution_type='bond'
        ),
        BaseForce(
            value=(np.full((n_atoms, 3), 2.0) * ureg.newton), contribution_type='angle'
        ),
        BaseForce(
            value=(np.full((n_atoms, 3), 3.0) * ureg.newton),
            contribution_type='coulomb',
        ),
    ]

    total = TotalForce(value=(np.zeros((n_atoms, 3)) * ureg.newton))
    total.contributions = contribs

    total.normalize(EntryArchive(), logger)
    assert total._is_contribution() is False
    assert all(c._is_contribution() for c in contribs)

    before = len(total.figures)
    total.normalize(EntryArchive(), logger)
    assert len(total.figures) == before
