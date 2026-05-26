from __future__ import annotations

from typing import TypedDict

from .registry import lookup_by_label


class BasisSetSpec(TypedDict):
    canonical_name: str


def spec_from_label(label: str) -> BasisSetSpec | None:
    """
    Build an internal canonical basis-set specification from a raw parsed label.

    Returns:
        BasisSetSpec if the label has an unambiguous lightweight registry match,
        otherwise None.
    """
    rec = lookup_by_label(label)
    if rec is None:
        return None

    return BasisSetSpec(
        canonical_name=rec['canonical_name'],
    )
