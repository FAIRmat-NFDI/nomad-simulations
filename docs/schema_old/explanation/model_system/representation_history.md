# Representation Architecture: Design History and Migration

This document captures the historical context and design decisions behind the `Representation` architecture for future reference and maintainers.

## The Problem with the Old Architecture

The previous design separated geometric properties across multiple inheritance layers, creating several issues:

1. **Excessive indirection**: Accessing cell data required navigating through subsections like `model_system.cell[0].lattice_vectors` instead of direct property access.

2. **Computed redundancy**: Properties such as `length_vector_a`, `length_vector_b`, `length_vector_c` and various angle properties were derived from `lattice_vectors` but stored as separate quantities, leading to potential inconsistencies.

3. **Unclear ownership**: Atomic positions resided on `ModelSystem` while cell information lived in a `Cell` subsection, splitting the description of the geometric structure across multiple locations.

4. **Fragmented hierarchy**: The inheritance chain `GeometricSpace` → `Cell` → `AtomicCell` distributed related properties across three classes, making it difficult to understand which properties were available at each level.

## The Unified Representation Solution

The new architecture addresses these issues through two key design patterns:

**Multiple Inheritance**: `ModelSystem` inherits from both `System` (NOMAD's base section class) and `Representation`, directly incorporating all geometric and structural properties. This reflects the fundamental truth that a model system is not just associated with a representation but is itself a spatially-defined entity.

**Composition for Alternatives**: While the primary representation data lives directly on `ModelSystem`, alternative views (primitive cells, conventional cells, supercells) are stored as `AlternativeRepresentation` instances in the `representations` subsection. This provides flexibility while maintaining a clear distinction between original and derived data.

## Migration Guide

For users familiar with the previous `Cell` and `AtomicCell` classes, here is a guide to updating your code:

### Property Access

| Old API | New API |
|---------|---------|
| `model_system.cell[0].lattice_vectors` | `model_system.lattice_vectors` |
| `model_system.cell[0].periodic_boundary_conditions` | `model_system.periodic_boundary_conditions` |
| `model_system.positions` | `model_system.positions` (unchanged) |
| `model_system.cell[0].wyckoff_letters` | `model_system.wyckoff_letters` |

### Creating Systems

**Old approach:**
```python
--8<-- "snippets/schema_old/explanation/model_system/representation_history/block_01.py"
```

**New approach:**
```python
--8<-- "snippets/schema_old/explanation/model_system/representation_history/block_02.py"
```

### Alternative Representations

**Old approach:**
```python
--8<-- "snippets/schema_old/explanation/model_system/representation_history/block_03.py"
```

**New approach:**
```python
--8<-- "snippets/schema_old/explanation/model_system/representation_history/block_04.py"
```

### Parser Migration

For parser developers, the typical pattern changes from creating subsections to populating direct properties:

**Old parser pattern:**
```python
--8<-- "snippets/schema_old/explanation/model_system/representation_history/block_05.py"
```

**New parser pattern:**
```python
--8<-- "snippets/schema_old/explanation/model_system/representation_history/block_06.py"
```

## Design Philosophy

The key innovation is that `ModelSystem` now directly inherits from `Representation`, providing immediate access to cell properties like `lattice_vectors` and `positions` without requiring navigation through nested subsections. Alternative representations of the same structure (such as primitive or conventional cells) are stored in the `representations` subsection, creating a clear separation between the original system description and derived or alternative views.

This design mirrors the approach used in the `ElectronicState` architecture, where a container class provides organizational structure while maintaining direct access to the essential properties of the system.

The direct access pattern is not only more concise but also more semantically clear: the model system itself has lattice vectors and positions, rather than containing a separate cell object with those properties.
