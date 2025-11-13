import json
from functools import lru_cache
from pathlib import Path

# Path to the registry JSON file
_REGISTRY_PATH = Path(__file__).parent / 'xc_registry_min.json'


def _keyize(s: str) -> str:
    # "XC_GGA_X_PBE" -> "GGAXPBE"
    return (
        s.strip()
        .upper()
        .replace('XC_', '')
        .replace('_', '')
        .replace('-', '')
        .replace(' ', '')
    )


@lru_cache(maxsize=1)
def _load_index() -> tuple[dict[str, dict], dict[int, dict], dict[str, dict]]:
    data: list[dict] = json.loads(_REGISTRY_PATH.read_text(encoding='utf-8'))
    by_key: dict[str, dict] = {_keyize(item['label']): item for item in data}
    by_id: dict[int, dict] = {int(item['id']): item for item in data}
    by_lbl: dict[str, dict] = {item['label']: item for item in data}
    return by_key, by_id, by_lbl


def lookup_by_label(label: str) -> dict | None:
    """Return the entry for a LibXC label. Accepts exact 'XC_*' or relaxed forms."""
    by_key, _, by_lbl = _load_index()
    if label in by_lbl:
        return by_lbl[label]
    return by_key.get(_keyize(label))


def lookup_by_id(xc_id: int) -> dict | None:
    """Return the entry with the given LibXC ID, or None if not found."""
    _, by_id, _ = _load_index()
    return by_id.get(int(xc_id))
