# Create interface system
interface = ModelSystem(is_representative=True)
interface.lattice_vectors = ...
interface.positions = ...

# Add particle states for both materials
for symbol in material_A_symbols + material_B_symbols:
    atom = AtomsState(chemical_symbol=symbol)
    interface.particle_states.append(atom)

# Define material A region as sub-system
material_A = ModelSystem(
    type='region',
    branch_label='Material A',
    particle_indices=list(range(len(material_A_symbols)))
)
interface.sub_systems.append(material_A)

# Define material B region as sub-system
material_B = ModelSystem(
    type='region',
    branch_label='Material B',
    particle_indices=list(range(len(material_A_symbols),
                                len(material_A_symbols) + len(material_B_symbols)))
)
interface.sub_systems.append(material_B)
