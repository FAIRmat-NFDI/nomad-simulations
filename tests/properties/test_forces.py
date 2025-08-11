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


def test_total_force_rejects_nested_contributions(caplog):
    n_atoms = 2
    deep_child = BaseForce(value=(np.zeros((n_atoms, 3)) * ureg.newton))
    child = BaseForce(value=(np.ones((n_atoms, 3)) * ureg.newton))
    child.contributions = [deep_child]  # illegal nesting

    total = TotalForce(value=(np.ones((n_atoms, 3)) * ureg.newton))
    total.contributions = [child]

    with caplog.at_level('ERROR'):
        total.normalize(EntryArchive(), logger)

    assert any('nested contributions' in rec.message.lower() for rec in caplog.records)


def test_contribution_type_on_total_force_main_is_error(caplog):
    n_atoms = 2
    a = BaseForce(value=(np.ones((n_atoms, 3)) * ureg.newton), contribution_type='lj')
    b = BaseForce(
        value=(np.ones((n_atoms, 3)) * ureg.newton), contribution_type='coulomb'
    )

    total = TotalForce(
        value=(np.zeros((n_atoms, 3)) * ureg.newton), contribution_type='invalid_main'
    )
    total.contributions = [a, b]

    with caplog.at_level('ERROR'):
        total.normalize(EntryArchive(), logger)

    assert any(
        'contribution_type set but is not a contribution' in rec.message.lower()
        for rec in caplog.records
    )
