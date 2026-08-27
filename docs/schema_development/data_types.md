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
