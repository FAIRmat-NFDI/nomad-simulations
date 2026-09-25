from nomad_simulations.schema_packages.model_system import (
    ModelSystem,
    AlternativeRepresentation
)

# Create model system with original cell data
model_system = ModelSystem()
model_system.lattice_vectors = original_lattice_vectors
model_system.positions = original_positions

# Add primitive cell representation
primitive_rep = AlternativeRepresentation(
    name='primitive',
    crystal_cell_type='primitive',
    lattice_vectors=primitive_lattice_vectors,
    transformation_matrix=primitive_transformation
)
model_system.representations.append(primitive_rep)

# Add conventional cell representation
conventional_rep = AlternativeRepresentation(
    name='conventional',
    crystal_cell_type='conventional',
    lattice_vectors=conventional_lattice_vectors
)
model_system.representations.append(conventional_rep)
