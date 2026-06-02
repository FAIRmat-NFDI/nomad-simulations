from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib.resources import files
from typing import Any, TypedDict

_SOURCE = 'Basis Set Exchange'
_REGISTRY_VERSION = 'basis-set-exchange-0.12'
_IGNORED_LABEL_CHARS = re.compile(r'[\s_-]+')


class BasisSetSpec(TypedDict):
    canonical_name: str


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
        }
    return registry


@lru_cache(maxsize=1)
def _index() -> dict[str, set[str]]:
    exact: dict[str, set[str]] = {}

    for key, rec in _registry().items():
        for label in (key, rec['canonical_name']):
            exact.setdefault(_normalize_label(label), set()).add(key)

    return exact


def lookup_by_label(label: str) -> dict[str, Any] | None:
    """
    Look up a lightweight canonical basis-set record from a raw parsed label.

    Matches are made against the registry key or canonical name.
    """
    if not label or not label.strip():
        return None

    normalized = _normalize_label(label)
    exact = _index()

    exact_matches = exact.get(normalized)
    if exact_matches is not None:
        if len(exact_matches) == 1:
            return _registry()[next(iter(exact_matches))]
        return None

    return None


def spec_from_label(label: str) -> BasisSetSpec | None:
    """
    Convert a raw parsed label to an internal canonical basis-set specification.

    Returns:
        BasisSetSpec if the label has a lightweight registry match, otherwise None.
    """
    rec = lookup_by_label(label)
    if rec is None:
        return None

    return BasisSetSpec(
        canonical_name=rec['canonical_name'],
    )


def source_name() -> str:
    return _SOURCE


def registry_version() -> str:
    return _REGISTRY_VERSION
