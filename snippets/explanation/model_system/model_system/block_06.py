# After normalization, access alternative representations
for rep in silicon.representations:
    if rep.name == 'primitive':
        print(f"Primitive cell volume: {rep.volume}")
    elif rep.name == 'conventional':
        print(f"Conventional cell lattice: {rep.lattice_vectors}")

# Convert specific representation to ASE Atoms object
primitive_atoms = silicon.to_ase_atoms(representation_index=0)
conventional_atoms = silicon.to_ase_atoms(representation_index=1)
