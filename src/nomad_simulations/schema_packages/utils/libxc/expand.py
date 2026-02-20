from __future__ import annotations

import json
import re
from collections.abc import Iterable
from functools import lru_cache
from importlib.resources import files

from .registry import lookup_by_label

# ---------------------------
# helpers
# ---------------------------

_OMEGA_MAP = str.maketrans({'ω': 'W', 'Ω': 'W', 'Ω': 'W'})
_TOKEN_SPLIT = re.compile(r'[+/,\s]+')


def _norm(s: str) -> str:
    """
    Uppercase, normalize omega, drop parentheses '(...)',
    and strip separators (space, +, /, _, -, comma).
    """
    s = (s or '').translate(_OMEGA_MAP).upper()
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'[\s+/,_-]+', '', s)
    return s


def _normkeys_lists(d: dict[str, list[str]]) -> dict[str, list[str]]:
    """Normalize dict keys where values are list[str]."""
    return {_norm(k): v for k, v in d.items()}


def _normkeys_strs(d: dict[str, str]) -> dict[str, str]:
    """Normalize dict keys where values are str."""
    return {_norm(k): v for k, v in d.items()}


@lru_cache(maxsize=4096)
def _exists(lbl: str) -> bool:
    """True if the LibXC label is present in the registry."""
    return lookup_by_label(lbl) is not None


def _existing(seq: Iterable[str]) -> list[str]:
    """Return only labels that exist in the registry."""
    return [x for x in seq if _exists(x)]


def _pick_best(candidates: list[list[str]]) -> list[str]:
    """
    From a list of candidate label-sets, return the first set that yields
    at least one existing label (keeping only existing ones).
    """
    for option in candidates:
        got = _existing(option)
        if got:
            return got
    return []


try:
    _ALIASES_PATH = files(__package__).joinpath('aliases.json')
    with _ALIASES_PATH.open('r', encoding='utf-8') as _f:
        _ALIASES = json.load(_f)
except Exception:
    _ALIASES = {}

_BASE: dict[str, list[str]] = _normkeys_lists(_ALIASES.get('BASE', {}))
_HYB: dict[str, list[str]] = _normkeys_lists(_ALIASES.get('HYB', {}))
_FALLBACK_BY_RUNG: dict[str, list[list[str]]] = _ALIASES.get('FALLBACK_BY_RUNG', {})
_RUNG_HINT: dict[str, str] = _normkeys_strs(_ALIASES.get('RUNG_HINT', {}))


def _labels_for_token(tok: str) -> list[str]:
    t = _norm(tok)
    if not t:
        return []

    # 1) exact LibXC label already?
    if t.startswith('XC_'):
        return _existing([t])

    # 2) explicit hybrids first
    if t in _HYB:
        got = _existing(_HYB[t])
        if got:
            return got

    # 3) base / (meta-)GGA aliases
    if t in _BASE:
        got = _existing(_BASE[t])
        if got:
            return got

    # 4) common synonyms after normalization
    if t in ('LCWPBE', 'LCOMEGAPBE'):  # LC-ωPBE
        got = _existing(_HYB['LC-ωPBE'])
        if got:
            return got
    if t == 'SOGGA11X':
        got = _existing(['XC_GGA_X_SOGGA11'])
        if got:
            return got

    # 5) rung-aware fallback if the specific labels aren’t present
    rung = _RUNG_HINT.get(t)
    if rung:
        return _pick_best(_FALLBACK_BY_RUNG.get(rung, []))

    return []


def expand_to_libxc_labels(raw: str) -> list[str]:
    """
    Conservative expansion of a raw XC string into LibXC labels:
      • Hybrids only when explicitly named.
      • Unknown tokens ignored.
      • Filters against the registry; if missing, rung-aware fallbacks fill the gap.
    """
    if not raw or not raw.strip():
        return []
    labels: set[str] = set()
    for tok in _TOKEN_SPLIT.split(raw):
        for lbl in _labels_for_token(tok):
            if lbl:
                labels.add(lbl)
    return sorted(labels)


def infer_rung_hint(raw: str) -> str | None:
    """
    Infer a Jacob's-ladder rung from alias hints in aliases.json.

    Returns the highest hinted rung found across tokens in `raw`, or None.
    """
    if not raw or not raw.strip():
        return None

    rank = {
        'LDA': 0,
        'GGA': 1,
        'meta-GGA': 2,
        'hybrid-GGA': 3,
        'hybrid-meta-GGA': 4,
    }
    best: str | None = None
    for tok in _TOKEN_SPLIT.split(raw):
        hinted = _RUNG_HINT.get(_norm(tok))
        if hinted is None:
            continue
        if best is None or rank.get(hinted, -1) > rank.get(best, -1):
            best = hinted
    return best
