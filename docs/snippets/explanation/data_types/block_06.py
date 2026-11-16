# Direct type serialization
original = m_float_bounded(dtype=float, bound=Bound('[0,1]'))
serialized = original.serialize_self()

# Reconstruction reloads the exact bounded class, keeping its bound
from nomad.metainfo.data_type import normalize_type
reconstructed = normalize_type(serialized)
# reconstructed is an m_float_bounded with bound [0,1]; the interval is still enforced
