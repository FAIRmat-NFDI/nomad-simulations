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
--8<-- "snippets/explanation/data_types/block_01.py"
```

### Interval Notation Examples

The `Bound` class supports standard mathematical interval notation:

```python
--8<-- "snippets/explanation/data_types/block_02.py"
```

### Common Masks

For common use cases, convenience functions are provided:

```python
--8<-- "snippets/explanation/data_types/block_03.py"
```

### Validation Behavior

Bounded types automatically validate values during assignment:

```python
--8<-- "snippets/explanation/data_types/block_04.py"
```

### Slack Tolerance and Soft Failure

By default a value outside the interval raises immediately. Three optional `Bound`
parameters relax that for quantities whose values are produced by approximate or
numerically noisy procedures, where a small excursion past a physical bound is an artifact
rather than a real error.

`slack` widens the accepted region into a *slack band* around the interval. It is a
**relative** fraction of the data's own peak magnitude: the effective tolerance for a given
check is `slack * max(|values|)`. Because it scales with the data, the same fraction is
meaningful across systems whose magnitudes differ by orders of magnitude, and it remains
usable when the bound sits at zero (e.g. a non-negative density of states, where an absolute
tolerance would be either negligible or physically distinct). Keep `slack` a small fraction,
sized to absorb numerical noise, never large enough to admit a physically distinct value.

`on_violation` selects what happens to values *beyond* the slack band: `'raise'` (the
default) aborts, while `'log'` emits a single structured warning and keeps processing.
`clamp` (when `True`) additionally snaps every out-of-interval value onto the nearest
endpoint; it requires every finite endpoint to be inclusive, so it cannot be combined with
an open finite bound.

```python
# Occupation numbers in [0, 2] that drift slightly out (e.g. MP2/CC natural orbitals):
# tolerate a small relative excursion, log it, and clamp back into range.
occupations = Quantity(
    type=m_float_bounded(
        dtype=np.float64,
        bound=Bound('[0,2]', slack=0.05, on_violation='log', clamp=True),
    ),
    shape=['*'],
)

# A non-negative spectral intensity: keep small negative lobes visible, only warn.
intensity = Quantity(
    type=m_float_bounded(
        dtype=np.float64,
        bound=Bound('[0,)', slack=0.01, on_violation='log', clamp=False),
    ),
    shape=['*'],
)
```

## Serialization and Deserialization

### Understanding the Behavior

The serialization and especially deserialization of bounded types vary on the context.
Here are the main distinguishing cases for deserialization.

#### Schema Context (Recommended Usage)

When bounded types are defined in schema quantities, serialization preserves the type information through the schema definition:

```python
--8<-- "snippets/explanation/data_types/block_05.py"
```

#### Standalone Type Serialization

Serializing a bounded type directly (without schema context) also preserves the bound.
The type serializes as a *custom* datatype -- recording its fully qualified class alongside the interval -- so `normalize_type` reloads the exact bounded class on reconstruction and the checks continue to apply.

```python
--8<-- "snippets/explanation/data_types/block_06.py"
```

## Error Handling

Bounded types provide clear error messages for constraint violations:

```python
--8<-- "snippets/explanation/data_types/block_08.py"
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
