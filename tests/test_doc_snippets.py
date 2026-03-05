import ast
import re
import runpy
from pathlib import Path

import numpy as np

from docs.snippets.data_types.basic_usage import build_valid_section
from docs.snippets.data_types.error_handling import bounded_error_message
from docs.snippets.data_types.factory_masks import factory_bounds_map
from docs.snippets.data_types.schema_context_roundtrip import schema_context_roundtrip
from docs.snippets.data_types.standalone_type_roundtrip import (
    standalone_type_roundtrip,
)
from docs.snippets.data_types.validation_behavior import demo_validation_behavior
from docs.snippets.model_system.alternative_representation_pattern import (
    alternative_representation_example,
)
from docs.snippets.model_system.minimal_parser_pattern import (
    minimal_model_system_example,
)
from docs.snippets.simulation_entry.program_setup import (
    build_simulation_with_program,
)

SNIPPETS_ROOT = Path('docs/snippets')
DOCS_ROOT = Path('docs')

# Snippets that are executed directly by tests in this file and therefore do
# not need to be included via --8<-- in markdown pages.
EXECUTED_SNIPPETS = {
    'snippets/data_types/basic_usage.py',
    'snippets/data_types/error_handling.py',
    'snippets/data_types/factory_masks.py',
    'snippets/data_types/schema_context_roundtrip.py',
    'snippets/data_types/standalone_type_roundtrip.py',
    'snippets/data_types/validation_behavior.py',
    'snippets/model_system/alternative_representation_pattern.py',
    'snippets/model_system/minimal_parser_pattern.py',
    'snippets/simulation_entry/program_setup.py',
}

# Standalone snippets that are not included in markdown pages but should still
# be checked as runnable examples.
RUNPY_SNIPPETS = {
    'snippets/data_types/interval_notation.py',
    'snippets/explanation/general/block_01.py',
}


def _doc_snippet_refs() -> list[str]:
    refs: set[str] = set()
    for md in DOCS_ROOT.rglob('*.md'):
        text = md.read_text(encoding='utf-8')
        refs.update(re.findall(r'--8<--\s+"([^"]+)"', text))
    # Ignore placeholder examples in guideline text.
    return sorted(r for r in refs if '<' not in r and '>' not in r)


def _all_snippet_files() -> list[str]:
    return sorted(
        str(path.relative_to(DOCS_ROOT))
        for path in SNIPPETS_ROOT.rglob('*.py')
        if path.name != '__init__.py'
    )


def test_minimal_model_system_example():
    model_system = minimal_model_system_example()
    assert model_system.is_representative is True
    assert len(model_system.particle_states) == 2
    assert model_system.periodic_boundary_conditions == [True, True, True]
    assert np.asarray(model_system.lattice_vectors.magnitude).shape == (3, 3)
    assert np.asarray(model_system.positions.magnitude).shape == (2, 3)


def test_alternative_representation_example():
    model_system = alternative_representation_example()
    assert len(model_system.representations) == 1
    rep = model_system.representations[0]
    assert rep.name == 'primitive'
    assert rep.crystal_cell_type == 'primitive'
    assert np.asarray(rep.lattice_vectors.magnitude).shape == (3, 3)


def test_data_types_basic_usage():
    section = build_valid_section()
    assert section.count == 3
    assert section.probability == 0.5
    assert section.energies == [0.1, 1.2, 3.4]


def test_data_types_factory_masks():
    bounds = factory_bounds_map()
    assert bounds['positive_int'] == '[0,)'
    assert bounds['strictly_positive_int'] == '[1,)'
    assert bounds['positive_float'] == '[0,)'
    assert bounds['strictly_positive_float'] == '(0,)'
    assert bounds['unit_float'] == '[0,1]'


def test_data_types_validation_behavior():
    valid_values, error_message = demo_validation_behavior()
    assert valid_values == [0.0, 0.5, 1.0]
    assert 'All values must be in [0.0,1.0]' in error_message


def test_data_types_schema_context_roundtrip():
    value = schema_context_roundtrip()
    assert value == 0.8


def test_data_types_standalone_roundtrip_behavior():
    original_class, reconstructed_class = standalone_type_roundtrip()
    assert original_class == 'm_float_bounded'
    # Current expected behavior: reconstructed type loses bound wrapper.
    assert reconstructed_class != 'm_float_bounded'


def test_data_types_error_message():
    message = bounded_error_message()
    assert 'All values must be in [0.0,1.0]' in message


def test_simulation_entry_program_setup():
    simulation = build_simulation_with_program()
    assert simulation.program is not None
    assert simulation.program.name == 'SUPERCODE'
    assert simulation.program.version == '7.0'


def test_all_markdown_referenced_snippet_paths_exist():
    refs = _doc_snippet_refs()
    assert refs, 'No snippet references found in docs markdown.'
    missing = [r for r in refs if not Path('docs', r).exists()]
    assert not missing, f'Missing snippet files: {missing}'


def test_all_markdown_referenced_python_snippets_are_syntax_valid():
    bad = []
    for ref in _doc_snippet_refs():
        if not ref.endswith('.py'):
            continue
        source = Path('docs', ref).read_text(encoding='utf-8')
        try:
            ast.parse(source)
        except SyntaxError as exc:
            bad.append(f'{ref}: {exc}')
    assert not bad, 'Invalid snippet syntax:\n' + '\n'.join(bad)


def test_all_snippet_python_files_are_syntax_valid():
    bad = []
    for ref in _all_snippet_files():
        source = Path('docs', ref).read_text(encoding='utf-8')
        try:
            ast.parse(source)
        except SyntaxError as exc:
            bad.append(f'{ref}: {exc}')
    assert not bad, 'Invalid snippet syntax:\n' + '\n'.join(bad)


def test_all_snippet_files_have_corresponding_test_coverage():
    refs = set(_doc_snippet_refs())
    covered = refs | EXECUTED_SNIPPETS | RUNPY_SNIPPETS
    all_snippets = set(_all_snippet_files())
    uncovered = sorted(all_snippets - covered)
    assert not uncovered, (
        'Snippets without coverage via markdown reference or executable test: '
        f'{uncovered}'
    )


def test_executed_snippet_list_is_valid():
    all_snippets = set(_all_snippet_files())
    unknown = sorted((set(EXECUTED_SNIPPETS) | set(RUNPY_SNIPPETS)) - all_snippets)
    assert not unknown, f'Executed snippet lists contain unknown paths: {unknown}'


def test_runpy_snippets_execute_without_error():
    for ref in sorted(RUNPY_SNIPPETS):
        runpy.run_path(str(Path('docs', ref)))
