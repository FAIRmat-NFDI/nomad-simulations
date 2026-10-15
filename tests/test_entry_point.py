import subprocess
import sys

import pytest

# Checks that run in a fresh interpreter: the test session itself has already imported
# every schema module, which hides import-order problems of the plugin entry point.
FRESH_INTERPRETER_CHECK = """
import sys
from nomad_simulations.schema_packages import nomad_simulations_plugin
nomad_simulations_plugin.load()
print(sys.modules.get({module!r}) is not None)
"""


@pytest.mark.integration
@pytest.mark.parametrize(
    'module, expected',
    [
        pytest.param(
            'nomad_simulations.schema_packages.basis_set',
            True,
            id='basis_set reached only through a lazy SectionProxy',
        ),
        pytest.param(
            'nomad_simulations.schema_packages.general',
            True,
            id='general is the package root',
        ),
    ],
)
def test_load_imports_lazily_referenced_modules(module: str, expected: bool) -> None:
    """
    `load()` must import every module that the schema reaches only through a lazily
    resolved `SectionProxy`. NOMAD registers the metainfo package of each imported
    module before it assembles the GUI metainfo; a module imported only later, while
    a reference is resolved during serialization, yields a reference into a package
    the GUI never receives.
    """
    result = subprocess.run(
        [sys.executable, '-c', FRESH_INTERPRETER_CHECK.format(module=module)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == str(expected)
