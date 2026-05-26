#!/usr/bin/env python3
"""
Generate reusable Markdown fragments used by hand-written explanation pages.

This script is intentionally lightweight and deterministic. It only writes files
under docs/snippets/generated/.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from nomad_simulations.schema_packages import model_method as model_method_module

OUT_DIR = Path('docs/snippets/generated')
HIERARCHY_FILE = OUT_DIR / 'model_method_hierarchy.md'
FAMILY_FILE = OUT_DIR / 'model_method_family_map.md'

HIERARCHY_CLASSES = [
    'BaseModelMethod',
    'ModelMethod',
    'ModelMethodElectronic',
]

METHOD_FAMILIES = [
    ('DFT', 'DFT'),
    ('TB', 'TB'),
    ('HF', 'HF'),
    ('CC', 'CC'),
    ('CI', 'CI'),
    ('Wannier', 'Wannier'),
    ('Slater-Koster', 'SlaterKoster'),
    ('Electronic Response Method', 'ElectronicResponseMethod'),
    ('GW', 'GW'),
    ('BSE', 'BSE'),
    ('TDDFT', 'TDDFT'),
    ('DMFT', 'DMFT'),
    ('EOM-CC', 'EOMCC'),
    ('ADC', 'ADC'),
    ('Excited-State Methodology', 'ExcitedStateMethodology'),
    ('Photon', 'Photon'),
]


def _one_line_doc(cls: type) -> str:
    doc = (cls.__doc__ or '').strip()
    if not doc:
        return 'No class description available.'
    parts = [line.strip() for line in doc.splitlines() if line.strip()]
    if not parts:
        return 'No class description available.'
    text = ' '.join(parts)
    first_sentence = text.split('. ', 1)[0].strip()
    if first_sentence and not first_sentence.endswith('.'):
        first_sentence += '.'
    return first_sentence


def _model_method_classes() -> dict[str, type]:
    classes: dict[str, type] = {}
    for name, obj in inspect.getmembers(model_method_module, inspect.isclass):
        if obj.__module__ != model_method_module.__name__:
            continue
        if not hasattr(obj, 'm_def'):
            continue
        classes[name] = obj
    return classes


def _render_hierarchy_fragment(classes: dict[str, type]) -> str:
    lines = [
        '<!-- AUTO-GENERATED: scripts/generate_explanation_fragments.py -->',
        '### Model Method Hierarchy (Generated)',
        '',
        '| Class | Description |',
        '|---|---|',
    ]
    for class_name in HIERARCHY_CLASSES:
        cls = classes.get(class_name)
        description = _one_line_doc(cls) if cls else 'Class not found in schema.'
        lines.append(f'| `{class_name}` | {description} |')
    lines += [
        '',
        'Source reference:',
        '- [Model Method (Schema Navigation)](../../schema/model_method.md)',
        '- [Model Method Electronic (Schema Navigation)](../../schema/model_method_electronic.md)',
        '',
    ]
    return '\n'.join(lines)


def _render_family_fragment(classes: dict[str, type]) -> str:
    lines = [
        '<!-- AUTO-GENERATED: scripts/generate_explanation_fragments.py -->',
        '### Key Method Families (Generated)',
        '',
        '| Family | Section Class | Description | Generated Reference |',
        '|---|---|---|---|',
    ]
    for family_label, class_name in METHOD_FAMILIES:
        cls = classes.get(class_name)
        if cls is None:
            continue
        description = _one_line_doc(cls)
        lines.append(
            '| '
            f'{family_label} | `{class_name}` | {description} | '
            '[Model Method Electronic](../../schema/model_method_electronic.md) |'
        )
    lines += [
        '',
        'Related generated references:',
        '- [Model Method Electronic](../../schema/model_method_electronic.md)',
        '- [Numerical Settings](../../schema/numerical_settings.md)',
        '- [Force Field](../../schema/force_field.md)',
        '',
    ]
    return '\n'.join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    classes = _model_method_classes()

    hierarchy_content = _render_hierarchy_fragment(classes)
    family_content = _render_family_fragment(classes)

    HIERARCHY_FILE.write_text(hierarchy_content, encoding='utf-8')
    FAMILY_FILE.write_text(family_content, encoding='utf-8')

    print(f'Wrote {HIERARCHY_FILE}')
    print(f'Wrote {FAMILY_FILE}')


if __name__ == '__main__':
    main()
