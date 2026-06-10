# Direct type serialization
original = m_float_bounded(dtype=float, bound=Bound('[0,1]'))
serialized = original.serialize_self()

# Reconstruction loses bounds information
from nomad.metainfo.data_type import normalize_type
reconstructed = normalize_type(serialized)
# Returns basic m_float64 without bounds!
