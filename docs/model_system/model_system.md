# `ModelSystem`

`ModelSystem` section represents the material system as used for the simulation input. It is defined in [src/nomad_simulations/schema_packages/model_system.py](https://github.com/nomad-coe/nomad-simulations/blob/develop/src/nomad_simulations/schema_packages/model_system.py) and inherits from the `System` base section. A `ModelSystem` may be a single configuration (e.g. a crystal or molecule), or one element in a parent-child tree used for complex systems (e.g., heterostructures or multi-component solutions).

The `ModelSystem` section encodes essential information such as:

- Name and Type
- Dimensionality
- Time Evolution

```python
ModelSystem (System)
├── cell (SubSection: Cell) [multiple instances allowed]
│    └── If cell is an AtomicCell (i.e. name == "AtomicCell"):
│           ├── positions, velocities, lattice_vectors, etc.
│           ├── atoms_state (repeated subsection holding individual AtomsState objects)
│           ├── n_atoms
│           ├── equivalent_atoms
│           └── wyckoff_letters
├── symmetry (SubSection: Symmetry) [multiple instances allowed]
│    ├── bravais_lattice
│    ├── hall_symbol
│    ├── point_group_symbol
│    ├── space_group_number
│    ├── space_group_symbol
│    ├── strukturbericht_designation
│    ├── prototype_formula
│    ├── prototype_aflow_id
│    └── atomic_cell_ref (points to one of the AtomicCell sections)
├── chemical_formula (SubSection: ChemicalFormula) [single instance]
│    ├── descriptive
│    ├── reduced
│    ├── iupac
│    ├── hill
│    └── anonymous
├── Branch properties:
│    ├── branch_label
│    ├── branch_depth
│    ├── atom_indices
│    ├── bond_list
│    └── composition_formula
└── model_system (SubSection: ModelSystem) [recursive nested ModelSystems]
     └── (Each nested ModelSystem follows the same structure as above)
```


!!! warning
    This part is still under construction.

    Currently the ModelSystem is being refactored.



    