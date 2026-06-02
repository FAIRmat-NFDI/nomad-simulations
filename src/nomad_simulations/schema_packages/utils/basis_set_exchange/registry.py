from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib.resources import files
from typing import Any

_SOURCE = 'Basis Set Exchange'
_REGISTRY_VERSION = 'basis-set-exchange-0.12'
_IGNORED_LABEL_CHARS = re.compile(r'[\s_-]+')


def _normalize_label(label: str) -> str:
    return _IGNORED_LABEL_CHARS.sub('', (label or '').casefold())


@lru_cache(maxsize=1)
def _registry() -> dict[str, dict[str, Any]]:
    path = files(__package__).joinpath('registry_min.json')
    with path.open('r', encoding='utf-8') as f:
        data: list[dict[str, Any]] = json.load(f)

    registry: dict[str, dict[str, Any]] = {}
    for rec in data:
        key = rec['key']
        registry[key] = {
            'canonical_key': key,
            'canonical_name': rec['canonical_name'],
            'aliases': rec.get('aliases', []),
        }
    return registry


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    exact: dict[str, set[str]] = {}
    aliases: dict[str, set[str]] = {}

    for key, rec in _registry().items():
        for label in (key, rec['canonical_name']):
            exact.setdefault(_normalize_label(label), set()).add(key)

        for alias in rec.get('aliases', []):
            aliases.setdefault(_normalize_label(alias), set()).add(key)

    return exact, aliases


def lookup_by_label(label: str) -> dict[str, Any] | None:
    """
    Look up a lightweight canonical basis-set record from a raw parsed label.

    Exact matches against the registry key or canonical name take
    precedence over aliases. Alias matches are accepted only when unambiguous.
    """
    if not label or not label.strip():
        return None

    normalized = _normalize_label(label)
    exact, aliases = _index()

    exact_matches = exact.get(normalized)
    if exact_matches is not None:
        if len(exact_matches) == 1:
            return _registry()[next(iter(exact_matches))]
        return None

    alias_matches = aliases.get(normalized)
    if alias_matches is None or len(alias_matches) != 1:
        return None

    return _registry()[next(iter(alias_matches))]


def source_name() -> str:
    return _SOURCE


def registry_version() -> str:
    return _REGISTRY_VERSION
