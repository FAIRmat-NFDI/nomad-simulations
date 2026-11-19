from docs.snippets.data_types.validation_behavior import ProbabilitySection


def bounded_error_message() -> str:
    section = ProbabilitySection()
    try:
        section.probability = 1.5
    except ValueError as exc:
        return str(exc)
    return ''
