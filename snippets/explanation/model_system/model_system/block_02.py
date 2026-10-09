from nomad_simulations.schema_packages.model_system import AlternativeRepresentation

primitive = AlternativeRepresentation(
    name='primitive',
    crystal_cell_type='primitive',
    lattice_vectors=primitive_lattice_vectors
)
model_system.representations.append(primitive)
