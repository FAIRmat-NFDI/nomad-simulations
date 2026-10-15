from nomad_simulations.schema_packages.atoms_state import AtomsState

model_system = ModelSystem()
for symbol in ['Si', 'Si']:
    atom = AtomsState(chemical_symbol=symbol)
    model_system.particle_states.append(atom)
