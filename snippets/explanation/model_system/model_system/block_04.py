# Create bulk system with an active site
bulk = ModelSystem(
    is_representative=True,
    lattice_vectors=...,
    # ... bulk properties
)

# Define active site as sub-system
active_site = ModelSystem(
    type='active_atom',
    particle_indices=[0, 5, 12]  # References particles in parent
)
bulk.sub_systems.append(active_site)

# Navigate down the hierarchy
for subsystem in bulk.sub_systems:
    # Each subsystem is itself a ModelSystem with direct access to geometry
    positions = subsystem.positions
    lattice = subsystem.lattice_vectors

    # And each can have its own alternative representations
    for rep in subsystem.representations:
        if rep.name == 'primitive':
            primitive_lattice = rep.lattice_vectors
