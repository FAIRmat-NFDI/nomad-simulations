from typing import Optional, Union

import numpy as np
import pytest
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.variables import (
    SpinChannel,
    MomentumTransfer,
)
from nomad_simulations.schema_packages.properties import ElectronicBandGap

from . import logger


@pytest.mark.parametrize(
    'bg_data, bg_type, spins, mom_trans',
    [
        ([1.0], None, None, None),
        ([1.0], 'direct', ['up'], [2 * [3 * [0]]]),
        ([1.0, 1.0], 'direct', ['up', 'down'], 2 * [2 * [3 * [0]]]),
        ([1.0], 'direct', ['up', 'down'], [2 * [3 * [0]]]),
    ],
)
def test_instantiation(bg_data, bg_type, spins, mom_trans):
    assert ElectronicBandGap(
        data=np.array(bg_data) * ureg.eV,
        type=bg_type,
        variables=[SpinChannel(data=spins), MomentumTransfer(data=mom_trans)],
    )
    # ! TODO add shape tests


@pytest.mark.parametrize(
    'bg_data, bg_type, moms, ref_moms',
    [
        ([1.0], None, [], []),
        ([1.0], None, [2 * [3 * [0.0]]], [2 * [3 * [0.0]]]),
        ([1.0], 'direct', [], [2 * [3 * [0.0]]]),
        ([1.0], 'indirect', [], []),
    ],
)
def test_direct_bandgap_normalization(
    bg_data: list[float],
    bg_type: Optional[str],
    moms: list[list[float]],
    ref_moms: list[list[float]],
):
    band_gap = ElectronicBandGap(
        data=np.array(bg_data) * ureg.eV,
        type=bg_type,
        variables=[MomentumTransfer(data=moms)] if moms else [],
    )
    band_gap.normalize(EntryArchive(), logger)

    var_moms = [
        var.m_to_dict()['data'][0]
        for var in band_gap.variables
        if isinstance(var, MomentumTransfer)
    ]
    assert var_moms == ref_moms
