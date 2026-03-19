import ast
import re
import runpy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from docs.snippets.data_types import error_handling as error_handling_module
from docs.snippets.data_types.basic_usage import build_valid_section
from docs.snippets.data_types.error_handling import bounded_error_message
from docs.snippets.data_types.factory_masks import factory_bounds_map
from docs.snippets.data_types.schema_context_roundtrip import schema_context_roundtrip
from docs.snippets.data_types.standalone_type_roundtrip import (
    standalone_type_roundtrip,
)
from docs.snippets.data_types.validation_behavior import demo_validation_behavior
from docs.snippets.explanation.general.block_01 import SUPERCODEParser
from docs.snippets.model_method.model_method_overview_example import (
    build_model_method_overview_example,
)
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
DEV_NOTES_ROOT = Path('.dev_notes')

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
    'snippets/model_method/model_method_overview_example.py',
    'snippets/model_system/minimal_parser_pattern.py',
    'snippets/simulation_entry/program_setup.py',
    'snippets/explanation/general/block_01.py',
}

SNIPPET_MARKER_PREFIX = '# docs-snippet:'
RUNNABLE_MARKER = 'runnable'
SKIP_COVERAGE_MARKER = 'skip-coverage'


def _doc_snippet_refs() -> list[str]:
    refs: set[str] = set()
    md_roots = [DOCS_ROOT]
    if DEV_NOTES_ROOT.exists():
        md_roots.append(DEV_NOTES_ROOT)

    for root in md_roots:
        for md in root.rglob('*.md'):
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


def _snippet_markers(ref: str) -> set[str]:
    markers: set[str] = set()
    for line in Path('docs', ref).read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped.startswith(SNIPPET_MARKER_PREFIX):
            continue
        tags = stripped.split(':', 1)[1]
        markers.update(tag.strip() for tag in tags.split(',') if tag.strip())
    return markers


def _marked_runnable_snippets() -> set[str]:
    return {
        ref for ref in _all_snippet_files() if RUNNABLE_MARKER in _snippet_markers(ref)
    }


def _coverage_skipped_snippets() -> set[str]:
    return {
        ref
        for ref in _all_snippet_files()
        if SKIP_COVERAGE_MARKER in _snippet_markers(ref)
    }


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


def test_data_types_error_message_no_error_path(monkeypatch):
    class NoErrorSection:
        probability = 0.5

    monkeypatch.setattr(error_handling_module, 'ProbabilitySection', NoErrorSection)
    assert bounded_error_message() == ''


def test_simulation_entry_program_setup():
    simulation = build_simulation_with_program()
    assert simulation.program is not None
    assert simulation.program.name == 'SUPERCODE'
    assert simulation.program.version == '7.0'


def test_model_method_overview_example():
    method = build_model_method_overview_example()
    assert method.name == 'DFT'
    assert method.type == 'KS'
    assert method.jacobs_ladder == 'GGA'
    assert method.numerical_settings is not None
    assert len(method.numerical_settings) == 1
    assert method.numerical_settings[0].n_max_iterations == 80


def test_supercode_parser_parse_example(tmp_path):
    mainfile = tmp_path / 'output.log'
    mainfile.write_text('version 7.3\n', encoding='utf-8')

    archive = SimpleNamespace(data=[])
    parser = SUPERCODEParser()
    parser.parse(str(mainfile), archive=archive, logger=None)

    assert len(archive.data) == 1
    simulation = archive.data[0]
    assert simulation.program.name == 'SUPERCODE'
    assert simulation.program.version == '7.3'


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
    covered = (
        refs
        | EXECUTED_SNIPPETS
        | _marked_runnable_snippets()
        | _coverage_skipped_snippets()
    )
    all_snippets = set(_all_snippet_files())
    uncovered = sorted(all_snippets - covered)
    assert not uncovered, (
        'Snippets without coverage via markdown reference or executable test: '
        f'{uncovered}'
    )


def test_executed_snippet_list_is_valid():
    all_snippets = set(_all_snippet_files())
    unknown = sorted(set(EXECUTED_SNIPPETS) - all_snippets)
    assert not unknown, f'Executed snippet lists contain unknown paths: {unknown}'


@pytest.mark.parametrize('ref', sorted(_marked_runnable_snippets()))
def test_marked_runnable_snippets_execute_without_error(ref):
    # Runnable markers are intended for standalone examples that execute on
    # import-like run (runpy) without extra fixtures.
    assert ref.endswith('.py')
    assert ref.startswith('snippets/')
    assert ref not in _coverage_skipped_snippets()
    runpy.run_path(str(Path('docs', ref)))


def test_skip_coverage_and_runnable_markers_do_not_overlap():
    overlap = _marked_runnable_snippets() & _coverage_skipped_snippets()
    assert not overlap, (
        f'Snippet cannot be both runnable and skip-coverage: {sorted(overlap)}'
    )


def test_runnable_marker_is_present_for_standalone_examples():
    # Guard against accidentally dropping marker coverage for standalone snippets.
    expected = {'snippets/data_types/interval_notation.py'}
    runnable = _marked_runnable_snippets()
    assert expected.issubset(runnable)
