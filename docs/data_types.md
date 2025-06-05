# Bounded Data Types

This guide covers the bounded data types provided by the nomad-schema-plugins-simulations package for enforcing value constraints on numeric data.

## Overview

### Objective

The bounded data types (`m_int_bounded` and `m_float_bounded`) extend NOMAD's standard integer and float types with mathematical interval bounds checking. They ensure that values assigned to schema quantities fall within specified ranges, providing automatic validation at the data model level.

### Key Features

- **Mathematical interval notation**: Support for standard interval notation like `[0,1]`, `(0,1)`, `[0,)`, etc.
- **Automatic validation**: Values are checked against bounds during normalization
- **Special value handling**: `None` and `NaN` values pass validation automatically
- **Array support**: Works with both scalar values and arrays (all elements are checked)
- **Unit compatibility**: Use NOMAD's unit system as usual

### Structure

The implementation consists of three main components:

1. **`Bound` class**: Parses and validates mathematical interval notation
2. **`m_int_bounded`**: Bounded integer data type extending `ExactNumber`
3. **`m_float_bounded`**: Bounded float data type extending `InexactNumber`

## How-To Guide

### Basic Usage in Schema Quantities

The most common usage is defining bounded quantities in NOMAD schemas:

```python
from nomad.metainfo import Quantity, Section
from nomad_simulations.schema_packages.data_types import (
    Bound, m_int_bounded, m_float_bounded
)

class MySection(Section):
    # Integer value constrained to [1, 10]
    count = Quantity(
        type=m_int_bounded(dtype=int, bound=Bound('[1,10]')),
        description='Number of items (1-10)'
    )
    
    # Float value constrained to [0.0, 1.0]
    probability = Quantity(
        type=m_float_bounded(dtype=float, bound=Bound('[0.0,1.0]')),
        description='Probability value (0.0-1.0)'
    )
    
    # Array of positive floats
    energies = Quantity(
        type=m_float_bounded(dtype=float, bound=Bound('(0,)')),
        shape=['*'],
        description='Energy values (strictly positive)'
    )
```

### Interval Notation Examples

The `Bound` class supports standard mathematical interval notation:

```python
# Closed intervals (inclusive bounds)
Bound('[0,1]')      # 0 ≤ x ≤ 1
Bound('[1,10]')     # 1 ≤ x ≤ 10

# Open intervals (exclusive bounds)  
Bound('(0,1)')      # 0 < x < 1
Bound('(-1,1)')     # -1 < x < 1

# Half-open intervals
Bound('[0,1)')      # 0 ≤ x < 1
Bound('(0,1]')      # 0 < x ≤ 1

# Unbounded intervals
Bound('[0,)')       # x ≥ 0 (non-negative)
Bound('(0,)')       # x > 0 (strictly positive)
Bound('(,10]')      # x ≤ 10 (upper bounded)
Bound('(,-1)')      # x < -1 (strictly negative)

# Unbounded (no constraints)
Bound('')           # No bounds (-∞, ∞)
```

### Common Masks

For common use cases, convenience functions are provided:

```python
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
```

### Validation Behavior

Bounded types automatically validate values during assignment:

```python
section = MySection()

# Valid assignments
section.probability = 0.5        # ✓ Valid
section.probability = 0.0        # ✓ Valid (inclusive bound)
section.probability = 1.0        # ✓ Valid (inclusive bound)

# Invalid assignments
section.probability = 1.5        # ✗ Raises ValueError
section.probability = -0.1       # ✗ Raises ValueError

# Special values (always valid)
section.probability = None       # ✓ Valid
section.probability = float('nan')  # ✓ Valid
```

## Serialization and Deserialization

### Understanding the Behavior

The serialization and especially deserialization of bounded types vary on the context.
Here are the main distinguishing cases for deserialization.

#### Schema Context (Recommended Usage)

When bounded types are defined in schema quantities, serialization preserves the type information through the schema definition:

```python
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
```

#### Standalone Type Serialization

When serializing bounded types directly (without schema context), bounds information may be lost.
This means that manipulating the variable (`reconstructed`), the bound checks no longer apply.

It is therefore recommended to **limit standalone deserialization** to cases where the original data may be considered immutable, e.g. data science pipelines.
When producing code that uses this approach, make sure to **test serialization roundtrips**, add comment properly, or use _custom serialization_.

```python
# Direct type serialization
original = m_float_bounded(dtype=float, bound=Bound('[0,1]'))
serialized = original.serialize_self()

# Reconstruction loses bounds information
from nomad.metainfo.data_type import normalize_type
reconstructed = normalize_type(serialized)
# Returns basic m_float64 without bounds!
```

### Custom Serialization (Advanced)

If you need to preserve bounds in standalone serialization, you can implement custom serialization:

```python
# Custom serialization preserving bounds
def serialize_bounded_type(bounded_type):
    return {
        'type_kind': 'custom',
        'type_data': f'{bounded_type.__class__.__module__}.{bounded_type.__class__.__name__}',
        'type_bound': str(bounded_type.bound),
    }

def deserialize_bounded_type(serialized):
    # Import the class and reconstruct with bounds
    module_path, class_name = serialized['type_data'].rsplit('.', 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    
    # Create instance and set bounds
    instance = cls()
    instance.bound = Bound(serialized['type_bound'])
    return instance
```

## Error Handling

Bounded types provide clear error messages for constraint violations:

```python
try:
    section.probability = 1.5
except ValueError as e:
    print(e)  # "All values must be in [0.0,1.0], got range [1.5, 1.5]"

try:
    section.values = [0.5, 2.0, 15.0]
except ValueError as e:
    print(e)  # "All values must be in [0,10], got range [0.5, 15.0]"
```

The error messages indicate:

- The expected bounds
- The actual range of values that caused the violation
- This helps quickly identify which values are problematic in large arrays

## Integration with NOMAD Features

Bounded types integrate seamlessly with other NOMAD features:

- **Archive validation**: Bounds are checked during archive processing
- **API validation**: REST API requests validate bounded values
- **GUI forms**: NOMAD's GUI can generate appropriate input controls
- **Search indexing**: Values are indexed normally for search operations
- **Export formats**: Bounded types work with all NOMAD export formats

This makes bounded types a robust solution for enforcing data quality constraints across the entire NOMAD ecosystem.
