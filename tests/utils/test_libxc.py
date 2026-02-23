import json
import re
from pathlib import Path

from nomad_simulations.schema_packages.utils.libxc import registry as libxc_registry


def _libxc_dir() -> Path:
    return Path(libxc_registry.__file__).parent


def _load_aliases() -> dict:
    aliases_path = _libxc_dir() / 'aliases.json'
    return json.loads(aliases_path.read_text(encoding='utf-8'))


def _load_registry_labels() -> set[str]:
    registry_path = _libxc_dir() / 'xc_registry_min.json'
    return {
        row['label'] for row in json.loads(registry_path.read_text(encoding='utf-8'))
    }


def _norm_alias_key(s: str) -> str:
    omega_map = str.maketrans({'ω': 'W', 'Ω': 'W', 'Ω': 'W'})
    s = (s or '').translate(omega_map).upper()
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'[\s+/,_-]+', '', s)
    return s


def test_registry_lookup_unknown_returns_none():
    assert libxc_registry.lookup_by_label('XC_DOES_NOT_EXIST_12345') is None
    assert libxc_registry.lookup_by_id(999_999_999) is None


def test_aliases_reference_only_registry_labels():
    aliases = _load_aliases()
    registry_labels = _load_registry_labels()
    referenced: set[str] = set()

    for section in ('BASE', 'HYB'):
        for labels in aliases.get(section, {}).values():
            referenced.update(labels)

    for options in aliases.get('FALLBACK_BY_RUNG', {}).values():
        for option in options:
            referenced.update(option)

    missing = sorted(referenced - registry_labels)
    assert not missing, (
        f'aliases.json references labels not present in xc_registry_min.json: {missing}'
    )


def test_aliases_have_no_key_collisions_after_normalization():
    aliases = _load_aliases()
    collisions: dict[str, list[str]] = {}

    for section in ('BASE', 'HYB', 'RUNG_HINT'):
        seen: dict[str, str] = {}
        for key in aliases.get(section, {}):
            normalized = _norm_alias_key(key)
            if normalized in seen:
                collisions.setdefault(
                    f'{section}:{normalized}', [seen[normalized]]
                ).append(key)
            else:
                seen[normalized] = key

    assert not collisions, f'aliases.json has normalized key collisions: {collisions}'


def test_rung_hints_are_structurally_valid():
    aliases = _load_aliases()
    fallbacks = aliases.get('FALLBACK_BY_RUNG', {})
    hints = aliases.get('RUNG_HINT', {})
    valid_families = {'LDA', 'GGA', 'meta-GGA', 'hybrid-GGA', 'hybrid-meta-GGA'}

    invalid_values = sorted({v for v in hints.values() if v not in valid_families})
    assert not invalid_values, (
        f'RUNG_HINT contains invalid family values: {invalid_values}'
    )

    undefined_fallbacks = sorted({v for v in hints.values() if v not in fallbacks})
    assert not undefined_fallbacks, (
        'RUNG_HINT references rung(s) without FALLBACK_BY_RUNG entries: '
        f'{undefined_fallbacks}'
    )
