def parse(self):
    model_system = ModelSystem()

    # Create cell subsection
    cell = AtomicCell()
    cell.lattice_vectors = self.get_lattice_vectors()
    cell.periodic_boundary_conditions = [True, True, True]
    model_system.cell.append(cell)

    # Positions on ModelSystem
    model_system.positions = self.get_positions()
