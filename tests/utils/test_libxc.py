import pytest
from nomad.datamodel import EntryArchive
from nomad_simulations.schema_packages.model_method import DFT, XCFunctional
from nomad_simulations.schema_packages.utils.libxc import registry as libxc_registry

from . import logger


def test_registry_lookup_unknown_returns_none():
    assert libxc_registry.lookup_by_label('XC_DOES_NOT_EXIST_12345') is None
    assert libxc_registry.lookup_by_id(999_999_999) is None
