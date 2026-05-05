from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from importlib.resources import files
from typing import Any
from urllib.parse import quote

_SOURCE = 'Basis Set Exchange'
_URL_TEMPLATE = 'https://www.basissetexchange.org/api/basis/{external_id}/format/json/?version={version}'
_WHITESPACE = re.compile(r'\s+')
_DASHES = str.maketrans(
    {
        '\u2010': '-',
        '\u2011': '-',
        '\u2012': '-',
        '\u2013': '-',
        '\u2014': '-',
        '\u2212': '-',
    }
)


def _normalize_label(label: str) -> str:
    label = unicodedata.normalize('NFKC', label or '').translate(_DASHES)
    label = _WHITESPACE.sub('', label)
    return label.casefold()


@lru_cache(maxsize=1)
def _registry() -> dict[str, dict[str, Any]]:
    path = files(__package__).joinpath('registry_min.json')
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, str], dict[str, set[str]]]:
    exact: dict[str, str] = {}
    aliases: dict[str, set[str]] = {}

    for key, rec in _registry().items():
        exact[_normalize_label(key)] = key
        exact[_normalize_label(rec['external_id'])] = key
        exact[_normalize_label(rec['canonical_name'])] = key

        for alias in rec.get('aliases', []):
            aliases.setdefault(_normalize_label(alias), set()).add(key)

    return exact, aliases


def lookup_by_label(label: str) -> dict[str, Any] | None:
    """
    Look up lightweight Basis Set Exchange metadata from a raw basis set label.

    Exact matches against the registry key, external ID, or canonical name take
    precedence over aliases. Alias matches are accepted only when unambiguous.
    """
    if not label or not label.strip():
        return None

    normalized = _normalize_label(label)
    exact, aliases = _index()

    key = exact.get(normalized)
    if key is not None:
        return _registry()[key]

    alias_matches = aliases.get(normalized)
    if alias_matches is None or len(alias_matches) != 1:
        return None

    return _registry()[next(iter(alias_matches))]


def source_name() -> str:
    return _SOURCE


def resource_url(external_id: str, version: str) -> str:
    return _URL_TEMPLATE.format(
        external_id=quote(external_id, safe=''), version=quote(version, safe='')
    )
