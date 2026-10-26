from nomad_simulations.schema_packages.data_types import (
    positive_int, strictly_positive_int,
    positive_float, strictly_positive_float,
    unit_float
)

class MySection(Section):
    # Non-negative integer (≥ 0)
    index = Quantity(
        type=positive_int(),
        description='Array index'
    )
    
    # Strictly positive integer (≥ 1)
    dimension = Quantity(
        type=strictly_positive_int(),
        description='Spatial dimension'
    )
    
    # Non-negative float (≥ 0.0)
    distance = Quantity(
        type=positive_float(),
        description='Distance value'
    )
    
    # Strictly positive float (> 0.0)
    temperature = Quantity(
        type=strictly_positive_float(),
        description='Temperature value'
    )
    
    # Unit interval [0.0, 1.0]
    weight = Quantity(
        type=unit_float(),
        description='Weight factor'
    )
