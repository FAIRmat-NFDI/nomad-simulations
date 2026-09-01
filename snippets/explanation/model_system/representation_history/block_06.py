def parse(self):
    model_system = ModelSystem()

    # Direct property assignment
    model_system.lattice_vectors = self.get_lattice_vectors()
    model_system.periodic_boundary_conditions = [True, True, True]
    model_system.positions = self.get_positions()
