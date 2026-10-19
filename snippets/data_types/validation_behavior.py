from nomad.metainfo import Quantity, Section

from nomad_simulations.schema_packages.data_types import Bound, m_float_bounded


class ProbabilitySection(Section):
    probability = Quantity(
        type=m_float_bounded(dtype=float, bound=Bound('[0.0,1.0]')),
        description='Probability value (0.0-1.0)',
    )


def demo_validation_behavior() -> tuple[list[float], str]:
    section = ProbabilitySection()
    valid_values = [0.0, 0.5, 1.0]
    for value in valid_values:
        section.probability = value

    error_message = ''
    try:
        section.probability = 1.5
    except ValueError as exc:
        error_message = str(exc)

    return valid_values, error_message
