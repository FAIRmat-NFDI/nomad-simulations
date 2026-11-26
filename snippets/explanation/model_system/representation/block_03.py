model_system = ModelSystem(is_representative=True)
model_system.lattice_vectors = ...
model_system.positions = ...

# Normalization triggers symmetry analysis
model_system.normalize(archive, logger)

# After normalization, alternative representations are populated
for rep in model_system.representations:
    if rep.name == 'primitive':
        primitive_lattice = rep.lattice_vectors
    elif rep.name == 'conventional':
        conventional_lattice = rep.lattice_vectors
