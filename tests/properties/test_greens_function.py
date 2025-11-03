from typing import Optional, Union

import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.properties import (
    QuasiparticleWeight,
)
from nomad_simulations.schema_packages.properties.greens_function import (
    BaseGreensFunction,
)
from nomad_simulations.schema_packages.variables import (
    Frequency,
    ImaginaryTime,
    KMesh,
    MatsubaraFrequency,
    Time,
    WignerSeitz,
)

from . import logger


def set_variables(
    gfs: BaseGreensFunction,
    variables: list[
        WignerSeitz | KMesh | Time | ImaginaryTime | Frequency | MatsubaraFrequency
    ],
) -> BaseGreensFunction:
    """
    Set the variables for the `BaseGreensFunction` class.
    """
    for variable in variables:
        if isinstance(variable, WignerSeitz):
            gfs.wigner_seitz = variable
        elif isinstance(variable, KMesh):
            gfs.k_mesh = variable
        elif isinstance(variable, Time):
            gfs.time = variable
        elif isinstance(variable, ImaginaryTime):
            gfs.imaginary_time = variable
        elif isinstance(variable, Frequency):
            gfs.real_frequency = variable
        elif isinstance(variable, MatsubaraFrequency):
            gfs.matsubara_frequency = variable
    return gfs


class TestBaseGreensFunction:
    """
    Test the `BaseGreensFunction` class defined in `properties/greens_function.py`.
    """

    @pytest.mark.parametrize(
        'variables, result',
        [
            ([], None),
            ([WignerSeitz()], 'r'),
            ([KMesh()], 'k'),
            ([Time()], 't'),
            ([ImaginaryTime()], 'it'),
            ([Frequency()], 'w'),
            ([MatsubaraFrequency()], 'iw'),
            ([WignerSeitz(), Time()], 'rt'),
            ([WignerSeitz(), ImaginaryTime()], 'rit'),
            ([WignerSeitz(), Frequency()], 'rw'),
            ([WignerSeitz(), MatsubaraFrequency()], 'riw'),
            ([KMesh(), Time()], 'kt'),
            ([KMesh(), ImaginaryTime()], 'kit'),
            ([KMesh(), Frequency()], 'kw'),
            ([KMesh(), MatsubaraFrequency()], 'kiw'),
        ],
    )
    def test_resolve_space_id(
        self,
        variables: list[
            WignerSeitz | KMesh | Time | ImaginaryTime | Frequency | MatsubaraFrequency
        ],
        result: str,
    ):
        """
        Test the `resolve_space_id` method of the `BaseGreensFunction` class.
        """
        gfs = BaseGreensFunction(n_atoms=1, n_correlated_orbitals=1)
        gfs = set_variables(gfs, variables)
        assert gfs.resolve_space_id() == result

    @pytest.mark.parametrize(
        'space_id, variables, result',
        [
            ('', [], None),  # empty `space_id`
            ('rt', [], None),  # `space_id` set by parser
            ('', [WignerSeitz()], 'r'),  # resolving `space_id`
            ('rt', [WignerSeitz()], 'r'),  # normalize overwrites `space_id`
            ('', [KMesh()], 'k'),
            ('', [Time()], 't'),
            ('', [ImaginaryTime()], 'it'),
            ('', [Frequency()], 'w'),
            ('', [MatsubaraFrequency()], 'iw'),
            ('', [WignerSeitz(), Time()], 'rt'),
            ('', [WignerSeitz(), ImaginaryTime()], 'rit'),
            ('', [WignerSeitz(), Frequency()], 'rw'),
            ('', [WignerSeitz(), MatsubaraFrequency()], 'riw'),
            ('', [KMesh(), Time()], 'kt'),
            ('', [KMesh(), ImaginaryTime()], 'kit'),
            ('', [KMesh(), Frequency()], 'kw'),
            ('', [KMesh(), MatsubaraFrequency()], 'kiw'),
        ],
    )
    def test_normalize(
        self,
        space_id: str,
        variables: list[
            WignerSeitz | KMesh | Time | ImaginaryTime | Frequency | MatsubaraFrequency
        ],
        result: str | None,
    ):
        """
        Test the `normalize` method of the `BaseGreensFunction` class.
        """
        gfs = BaseGreensFunction(n_atoms=1, n_correlated_orbitals=1)
        gfs = set_variables(gfs, variables)
        gfs.space_id = space_id if space_id else None
        gfs.normalize(archive=EntryArchive(), logger=logger)
        assert gfs.space_id == result


class TestQuasiparticleWeight:
    """
    Test the `QuasiparticleWeight` class defined in `properties/greens_function.py`.
    """

    @pytest.mark.parametrize(
        'value, result',
        [
            ([[1, 0.9, 0.8]], 'non-correlated metal'),
            ([[0.2, 0.3, 0.1]], 'strongly-correlated metal'),
            ([[0, 0.3, 0.1]], 'OSMI'),
            ([[0, 0, 0]], 'Mott insulator'),
            ([[1.0, 0.8, 0.2]], None),
        ],
    )
    def test_resolve_system_correlation_strengths(
        self, value: list[float], result: str | None
    ):
        """
        Test the `resolve_system_correlation_strengths` method of the `QuasiparticleWeight` class.
        """
        quasiparticle_weight = QuasiparticleWeight(
            n_atoms=1, n_correlated_orbitals=3, value=value
        )
        assert quasiparticle_weight.resolve_system_correlation_strengths() == result

    @pytest.mark.parametrize(
        'value, reference',
        [
            ([[1, 0.5, -2]], ''),
            ([[1, 0.5, 8]], ''),
            ([[1, 0.9, 0.8]], 'non-correlated metal'),
            ([[0.2, 0.3, 0.1]], 'strongly-correlated metal'),
            ([[0, 0.3, 0.1]], 'OSMI'),
            ([[0, 0, 0]], 'Mott insulator'),
            # ? ([[1.0, 0.8, 0.2]], ''),
        ],
    )
    def test_normalize(self, value: list[float], reference: str):
        """
        Test the `normalize` method of the `QuasiparticleWeight` class.
        """
        if reference == '':
            with pytest.raises(ValueError, match=r'All values must be in \[0,1\]'):
                QuasiparticleWeight(n_atoms=1, n_correlated_orbitals=3, value=value)
        else:
            quasiparticle_weight = QuasiparticleWeight(
                n_atoms=1, n_correlated_orbitals=3, value=value
            )
            quasiparticle_weight.normalize(archive=EntryArchive(), logger=logger)
            assert quasiparticle_weight.system_correlation_strengths == reference
