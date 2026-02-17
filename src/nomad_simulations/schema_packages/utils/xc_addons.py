from __future__ import annotations

import re

_NONLOCAL_SUFFIX_RE = re.compile(
    r'^(?P<base>.+?)\s*\+\s*(?P<addon>RVV10|VV10)\s*$',
    re.IGNORECASE,
)


def split_xc_and_addons(raw: str) -> tuple[str | None, str | None, str | None]:
    """
    Split an XC key into baseline XC and optional add-ons.

    Returns:
        (base_xc_key, explicit_dispersion_suffix, nonlocal_corr_addon)

    Notes:
    - For now, only nonlocal-correlation add-ons are recognized: +VV10 / +rVV10.
    - Unknown forms are left untouched as the base XC key.
    """
    if raw is None:
        return None, None, None

    text = raw.strip()
    if not text:
        return None, None, None

    match = _NONLOCAL_SUFFIX_RE.match(text)
    if not match:
        return text, None, None

    base_xc_key = match.group('base').strip() or None
    addon_raw = match.group('addon').upper()
    nonlocal_corr_addon = 'rVV10' if addon_raw == 'RVV10' else 'VV10'

    return base_xc_key, None, nonlocal_corr_addon
