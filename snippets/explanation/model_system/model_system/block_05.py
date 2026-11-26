from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.atoms_state import AtomsState
import numpy as np
from nomad.units import ureg

# Create silicon crystal
silicon = ModelSystem(is_representative=True)

# Set cell geometry
silicon.lattice_vectors = np.array([
    [5.43, 0.0, 0.0],
    [0.0, 5.43, 0.0],
    [0.0, 0.0, 5.43]
]) * ureg.angstrom
silicon.periodic_boundary_conditions = [True, True, True]

# Add atoms
positions = np.array([
    [0.0, 0.0, 0.0],
    [1.3575, 1.3575, 1.3575]
]) * ureg.angstrom
silicon.positions = positions

for i in range(2):
    atom = AtomsState(chemical_symbol='Si')
    silicon.particle_states.append(atom)

# Normalization will generate symmetry info and chemical formulas
# (archive and logger are provided by the NOMAD normalization context)
silicon.normalize(archive, logger)

# Access results
print(f"Space group: {silicon.symmetry.space_group_number}")
print(f"Formula: {silicon.chemical_formula.reduced}")
