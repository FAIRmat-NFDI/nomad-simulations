from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from meta_introspect import iter_section_classes
from verticals import VERTICALS

WORKFLOW_VERTICAL_PREFIX = 'workflow'
ALLOWED_EXTERNAL_ANCHORS = {
    'NumericalSettings',
    'PhysicalProperty',
}


def _workflow_schema_classes() -> set[str]:
    classes = set()
    for cls in iter_section_classes('nomad_simulations'):
        if cls.__module__.startswith('nomad_simulations.schema_packages.workflow'):
            classes.add(cls.__name__)
    return classes


def _workflow_vertical_sections() -> set[str]:
    sections = set()
    for key, spec in VERTICALS.items():
        if not key.startswith(WORKFLOW_VERTICAL_PREFIX):
            continue
        if not isinstance(spec, dict):
            continue
        sections.update(spec.get('sections', []))
    return sections


def test_all_workflow_schema_classes_are_documented_in_workflow_verticals():
    workflow_classes = _workflow_schema_classes()
    documented_sections = _workflow_vertical_sections()

    missing = sorted(workflow_classes - documented_sections)
    assert not missing, (
        'Workflow schema classes missing from workflow vertical docs: '
        + ', '.join(missing)
    )


def test_workflow_verticals_only_reference_workflow_classes_or_allowed_anchors():
    workflow_classes = _workflow_schema_classes()
    documented_sections = _workflow_vertical_sections()

    unexpected = sorted(
        documented_sections - workflow_classes - ALLOWED_EXTERNAL_ANCHORS
    )
    assert not unexpected, (
        'Workflow verticals reference unexpected non-workflow classes: '
        + ', '.join(unexpected)
    )
