from nomad_simulations.schema_packages.data_types import (
    positive_float,
    positive_int,
    strictly_positive_float,
    strictly_positive_int,
    unit_float,
)


def factory_bounds_map() -> dict[str, str]:
    """Return the bounds behind convenience factory functions."""
    return {
        'positive_int': str(positive_int().bound),
        'strictly_positive_int': str(strictly_positive_int().bound),
        'positive_float': str(positive_float().bound),
        'strictly_positive_float': str(strictly_positive_float().bound),
        'unit_float': str(unit_float().bound),
    }
