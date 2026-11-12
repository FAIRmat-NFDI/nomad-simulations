from nomad_simulations.schema_packages.model_system import ModelSystem
import numpy as np

# Create a model system
model_system = ModelSystem()

# Set lattice vectors (each row is a vector in the implicit Cartesian frame)
model_system.lattice_vectors = np.array([
    [5.0, 0.0, 0.0],  # lattice vector a
    [0.0, 5.0, 0.0],  # lattice vector b
    [0.0, 0.0, 5.0]   # lattice vector c
]) * ureg.angstrom

model_system.periodic_boundary_conditions = [True, True, True]

# Set positions in Cartesian coordinates
model_system.positions = np.array([
    [0.0, 0.0, 0.0],
    [2.5, 2.5, 2.5]
]) * ureg.angstrom

# Alternatively, use fractional coordinates
model_system.fractional_coordinates = np.array([
    [0.0, 0.0, 0.0],
    [0.5, 0.5, 0.5]
])
