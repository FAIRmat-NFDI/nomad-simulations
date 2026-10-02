model_system = ModelSystem()
cell = AtomicCell(
    type='original',
    lattice_vectors=lattice,
    periodic_boundary_conditions=[True, True, True]
)
model_system.cell.append(cell)
