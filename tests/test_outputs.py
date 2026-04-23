from typing import Optional

import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.outputs import (
    Outputs,
)
from nomad_simulations.schema_packages.properties import ElectronicBandGap

from . import logger
from .conftest import generate_simulation  # generate_scf_electronic_band_gap_template


class TestOutputs:
    """
    Test the `Outputs` class defined in `outputs.py`.
    """

    @pytest.mark.parametrize(
        'band_gaps, values, result_length, result',
        [
            # no properties to extract
            ([], [], 0, []),
            # non-spin polarized case
            ([ElectronicBandGap()], [2.0], 0, []),
            # spin polarized case
            (
                [
                    ElectronicBandGap(spin_channel=0),
                    ElectronicBandGap(spin_channel=1),
                ],
                [1.0, 1.5],
                2,
                [
                    ElectronicBandGap(spin_channel=0),
                    ElectronicBandGap(spin_channel=1),
                ],
            ),
        ],
    )
    def test_extract_spin_polarized_properties(
        self,
        band_gaps: list[ElectronicBandGap],
        values: list[float],
        result_length: int,
        result: list[ElectronicBandGap],
    ):
        """
        Test the `extract_spin_polarized_property` method.

        Args:
            band_gaps (list[ElectronicBandGap]): The `ElectronicBandGap` sections to be stored under `Outputs`.
            values (list[float]): The values to be assigned to the `ElectronicBandGap` sections.
            result_length (int): The expected length extracted from `extract_spin_polarized_property`.
            result (list[ElectronicBandGap]): The expected result of the `extract_spin_polarized_property` method.
        """
        outputs = Outputs()

        for i, band_gap in enumerate(band_gaps):
            band_gap.value = values[i]
            outputs.electronic_band_gaps.append(band_gap)
        gaps = outputs.extract_spin_polarized_property(
            property_name='electronic_band_gaps'
        )
        assert len(gaps) == result_length
        if len(result) > 0:
            for i, result_gap in enumerate(result):
                result_gap.value = values[i]
                # ? comparing the sections does not work
                assert gaps[i].value == result_gap.value
        else:
            assert gaps == result

    @pytest.mark.parametrize(
        'model_systems, outputs_list',
        [
            # empty lists
            ([], []),
            # single element
            ([ModelSystem(name='system_0')], [Outputs()]),
            # 3 elements
            (
                [
                    ModelSystem(name='system_0'),
                    ModelSystem(name='system_1'),
                    ModelSystem(name='system_2'),
                ],
                [Outputs(), Outputs(), Outputs()],
            ),
            # mismatched lengths
            ([ModelSystem(name='system_0')], [Outputs(), Outputs()]),
            ([ModelSystem(name='system_0'), ModelSystem(name='system_1')], [Outputs()]),
        ],
    )
    def test_set_model_system_ref(
        self, model_systems: list[ModelSystem], outputs_list: list[Outputs]
    ):
        """
        Test the `set_model_system_ref` method with 1-1 mapping between model_system and outputs.

        Args:
            model_systems (list[ModelSystem]): List of `ModelSystem` objects to be tested.
            outputs_list (list[Outputs]): List of `Outputs` objects to be tested.
        """
        simulation = generate_simulation()
        simulation.model_system = model_systems
        simulation.outputs = outputs_list

        for i, output in enumerate(outputs_list):
            output.m_parent = simulation
            output.m_parent_index = i

            model_system_ref = output.set_model_system_ref()

            if len(model_systems) == len(outputs_list) and len(model_systems) > 0:
                assert model_system_ref == model_systems[i]
                assert model_system_ref.name == f'system_{i}'
            elif len(model_systems) > 0:
                assert model_system_ref == model_systems[-1]
            else:
                assert model_system_ref is None

    def test_set_model_system_ref_prefers_representative_system_on_mismatch(self):
        """
        When model_system and outputs lengths mismatch, use representative_system_index.

        This validates the fallback chain: with 3 model_systems and 2 outputs, the
        1:1 mapping does not apply, so `set_model_system_ref()` should use
        `representative_system_index` instead of later fallbacks.
        """
        simulation = generate_simulation()
        simulation.model_system = [
            ModelSystem(name='system_0'),
            ModelSystem(name='system_1'),
            ModelSystem(name='system_2'),
        ]
        simulation.representative_system_index = 0
        simulation.outputs = [Outputs(), Outputs()]

        output = simulation.outputs[0]
        output.m_parent = simulation
        output.m_parent_index = 0

        model_system_ref = output.set_model_system_ref()
        assert model_system_ref == simulation.model_system[0]
        assert model_system_ref.name == 'system_0'

    @pytest.mark.parametrize(
        'model_method',
        [(None), (ModelMethod(name='example'))],
    )
    def test_set_model_method_ref(self, model_method: ModelMethod | None):
        """
        Test the `set_model_method_ref` method.

        Args:
            model_method (Optional[ModelMethod]): The `ModelMethod` to be tested for the `model_method_ref` reference
            stored in `Outputs`.
        """
        outputs = Outputs()
        simulation = generate_simulation(
            model_method=[model_method] if model_method else [], outputs=[outputs]
        )
        model_method_ref = outputs.set_model_method_ref()
        if model_method is not None:
            assert model_method_ref == simulation.model_method[-1]
            assert model_method_ref.name == 'example'
        else:
            assert model_method_ref is None

    @pytest.mark.parametrize(
        'model_system, model_method',
        [
            (None, None),
            (ModelSystem(name='example system'), None),
            (None, ModelMethod(name='example method')),
            (ModelSystem(name='example system'), ModelMethod(name='example method')),
        ],
    )
    def test_normalize(
        self, model_system: ModelSystem | None, model_method: ModelMethod | None
    ):
        """
        Test the `normalize` method.

        Args:
            model_system (Optional[ModelSystem]): The expected `model_system_ref` obtained after normalization and
            initially stored under `Simulation.model_system[0]`.
            model_method (Optional[ModelMethod]): The expected `model_method_ref` obtained after normalization and
            initially stored under `Simulation.model_method[0]`.
        """
        outputs = Outputs()
        simulation = generate_simulation(
            model_system=[model_system] if model_system else [],
            model_method=[model_method] if model_method else [],
            outputs=[outputs],
        )
        outputs.normalize(archive=EntryArchive(), logger=logger)
        if model_system is not None:
            assert outputs.model_system_ref == simulation.model_system[-1]
            assert outputs.model_system_ref.name == 'example system'
        else:
            assert outputs.model_system_ref is None
        if model_method is not None:
            assert outputs.model_method_ref == simulation.model_method[-1]
            assert outputs.model_method_ref.name == 'example method'
        else:
            assert outputs.model_method_ref is None
