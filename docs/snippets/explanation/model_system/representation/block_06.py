# At any level of the hierarchy, access alternative geometric views
for rep in model_system.representations:
    if rep.name == 'primitive':
        primitive_lattice = rep.lattice_vectors
    elif rep.name == 'conventional':
        conventional_lattice = rep.lattice_vectors
