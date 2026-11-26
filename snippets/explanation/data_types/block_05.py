class MySchema(Section):
    bounded_value = Quantity(
        type=m_float_bounded(dtype=float, bound=Bound('[0,1]')),
        description='Bounded value'
    )

# Create and populate
section = MySchema()
section.bounded_value = 0.5

# Serialize and deserialize
serialized = section.m_to_dict()
reconstructed = MySchema.m_from_dict(serialized)

# Bounds checking still works!
reconstructed.bounded_value = 0.8  # ✓ Valid
reconstructed.bounded_value = 1.5  # ✗ Still raises ValueError
