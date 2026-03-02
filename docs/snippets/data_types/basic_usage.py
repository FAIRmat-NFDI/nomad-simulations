from nomad.metainfo import Quantity, Section

from nomad_simulations.schema_packages.data_types import Bound, m_float_bounded, m_int_bounded


class MySection(Section):
    # Integer value constrained to [1, 10]
    count = Quantity(
        type=m_int_bounded(dtype=int, bound=Bound('[1,10]')),
        description='Number of items (1-10)',
    )

    # Float value constrained to [0.0, 1.0]
    probability = Quantity(
        type=m_float_bounded(dtype=float, bound=Bound('[0.0,1.0]')),
        description='Probability value (0.0-1.0)',
    )

    # Array of strictly positive floats
    energies = Quantity(
        type=m_float_bounded(dtype=float, bound=Bound('(0,)')),
        shape=['*'],
        description='Energy values (strictly positive)',
    )


def build_valid_section() -> MySection:
    section = MySection()
    section.count = 3
    section.probability = 0.5
    section.energies = [0.1, 1.2, 3.4]
    return section
