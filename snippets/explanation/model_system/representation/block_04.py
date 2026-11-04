# Convert using original cell geometry from ModelSystem
atoms_original = model_system.to_ase_atoms()

# Convert using primitive cell geometry from representations[0]
atoms_primitive = model_system.to_ase_atoms(representation_index=0)

# Convert using conventional cell geometry from representations[1]
atoms_conventional = model_system.to_ase_atoms(representation_index=1)
