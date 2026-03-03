primitive_rep = None
for rep in model_system.representations:
    if rep.name == 'primitive':
        primitive_rep = rep
        break

if primitive_rep:
    # Use the primitive representation
    primitive_lattice = primitive_rep.lattice_vectors
