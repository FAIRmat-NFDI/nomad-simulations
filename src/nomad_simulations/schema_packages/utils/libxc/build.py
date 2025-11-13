from __future__ import annotations

from typing import Optional, TypedDict

from .registry import lookup_by_id, lookup_by_label


class XCComponentSpec(TypedDict):
    libxc_id: int
    canonical_label: str
    display_name: str
    family: str
    kind: str
    weight: float


def spec_from_label(label: str, *, weight: float = 1.0) -> XCComponentSpec | None:
    """
    Build a plain-data specification for an XCComponent from a LibXC-style label.

    Returns:
        XCComponentSpec if found, otherwise None.
    """
    rec = lookup_by_label(label)
    if not rec:
        return None

    return XCComponentSpec(
        libxc_id=rec['id'],
        canonical_label=rec['label'],
        display_name=rec['name'],
        family=rec['family'],
        kind=rec['kind'],
        weight=float(weight),
    )


def spec_from_id(xc_id: int, *, weight: float = 1.0) -> XCComponentSpec | None:
    """
    Build a plain-data specification for an XCComponent from a LibXC integer ID.

    Returns:
        XCComponentSpec if found, otherwise None.
    """
    rec = lookup_by_id(xc_id)
    if not rec:
        return None
    return spec_from_label(rec['label'], weight=weight)
