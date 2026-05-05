from __future__ import annotations

from typing import TypedDict

from .registry import lookup_by_label, resource_url, source_name


class ExternalBasisSetReferenceSpec(TypedDict):
    source: str
    external_id: str
    version: str
    canonical_name: str
    url: str


def reference_from_label(label: str) -> ExternalBasisSetReferenceSpec | None:
    """
    Build external basis set reference metadata from a raw parsed basis set label.

    Returns:
        ExternalBasisSetReferenceSpec if the label has an unambiguous lightweight
        Basis Set Exchange metadata match, otherwise None.
    """
    rec = lookup_by_label(label)
    if rec is None:
        return None

    external_id = rec['external_id']
    version = rec['version']
    return ExternalBasisSetReferenceSpec(
        source=source_name(),
        external_id=external_id,
        version=version,
        canonical_name=rec['canonical_name'],
        url=resource_url(external_id, version),
    )
