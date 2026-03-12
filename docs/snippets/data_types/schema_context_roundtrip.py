from nomad.metainfo import Quantity, Section

from nomad_simulations.schema_packages.data_types import Bound, m_float_bounded


class MySchema(Section):
    bounded_value = Quantity(
        type=m_float_bounded(dtype=float, bound=Bound('[0,1]')),
        description='Bounded value',
    )


def schema_context_roundtrip() -> float:
    section = MySchema()
    section.bounded_value = 0.5

    serialized = section.m_to_dict()
    reconstructed = MySchema.m_from_dict(serialized)
    reconstructed.bounded_value = 0.8
    return reconstructed.bounded_value
