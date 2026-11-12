from nomad.metainfo.data_type import normalize_type

from nomad_simulations.schema_packages.data_types import Bound, m_float_bounded


def standalone_type_roundtrip() -> tuple[str, str]:
    original = m_float_bounded(dtype=float, bound=Bound('[0,1]'))
    serialized = original.serialize_self()
    reconstructed = normalize_type(serialized)
    return str(original.__class__.__name__), str(reconstructed.__class__.__name__)
