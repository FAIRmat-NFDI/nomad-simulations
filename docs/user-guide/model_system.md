# `ModelSystem`

`ModelSystem` section represents the material system as used for the simulation input. It is defined in [src/nomad_simulations/schema_packages/model_system.py](https://github.com/nomad-coe/nomad-simulations/blob/develop/src/nomad_simulations/schema_packages/model_system.py) and inherits from the `System` base section. A `ModelSystem` may be a single configuration (e.g. a crystal or molecule), or one element in a parent-child tree used for complex systems (e.g., heterostructures or multi-component solutions).


The `ModelSystem` section encodes everything you need to describe the atomic configuration (or hierarchy of configurations) that your simulation acts on. Internally it extends NOMAD’s core `System` and adds:

- **Top-level positions** (`positions`) and **per-atom states** (`particle_states`)
- Support for **hierarchical subsystems** (`sub_systems`) with branching properties
- Helpers to go **to/from** ASE `Atoms` objects
- Automatic **type**, **dimensionality**, **symmetry** and **chemical formula** inference on normalization

---

## Core quantities

| Name                 | Type                            | Description                                                                                       |
|----------------------|---------------------------------|---------------------------------------------------------------------------------------------------|
| `name`               | `str`                           | Optional verbose label (e.g. “hBN/G/hBN”).                                                        |
| `type`               | Enum{`atom`,`bulk`,…}           | Automatically determined: atom, molecule/cluster, 1D, surface, 2D, bulk, etc.                     |
| `dimensionality`     | `int`                           | 0–3, determined by MatID topology‐scaling or ASE connectivity.                                     |
| `is_representative`  | `bool`                          | Only “representative” systems are normalized (default False).                                      |
| `time_step`          | `int`                           | If you store multiple time‐snapshots under `Simulation`, this tags each one.                       |
| **Cell**             | SubSection `Cell` (repeatable)  | One or more cell definitions (original/primitive/conventional).                                    |
| **Symmetry**         | SubSection `Symmetry` (repeatable) | Space‐group/punkt‐group info + derived “primitive” & “conventional” cells via MatID.               |
| **ChemicalFormula**  | SubSection `ChemicalFormula`    | IUPAC, Hill, reduced, anonymous formats — inferred from ASE Atoms.                                 |
| `positions`          | `float[n_particles,3]`          | Cartesian coordinates for _all_ atoms (in metres).                                                |
| `n_particles`        | `int`                           | Number of atoms (populated by `from_ase_atoms`, or you can set manually).                          |
| **particle_states**  | SubSection `ParticleState` (→ `AtomsState`) | Per‐atom electronic state info; each entry holds `chemical_symbol`, `atomic_number`, `orbitals_state`, etc. |
| **sub_systems**      | recursive SubSection `ModelSystem` | For grouping/branching (e.g. molecule→atoms, heterostructure→components).                           |
| `branch_label`       | `str`                           | Name for this branch (e.g. “group_H2O”).                                                          |
| `branch_depth`       | `int`                           | Depth in the tree (root 0, its children 1, etc.).                                                 |
| `particle_indices`   | `int[*]`                        | Indices into parent’s `positions` / `particle_states` for this child.                              |
| `bond_list`          | `int[*][2]`                     | Optional list of bonded‐atom index pairs.                                                         |
| `composition_formula`| `str`                           | e.g. `H(1)O(2)`, `group_H2O(1)H2O(3)`, etc., auto‐filled by normalization.                        |
| `total_charge`, `total_spin` | `int`                  | Overall system charge and spin multiplicity.                                                      |

---

## Key methods

```python
model = ModelSystem(is_representative=True)

# add a cell
from nomad_simulations.schema_packages.model_system import AtomicCell
import numpy as np, nomad_units as ureg
cell = AtomicCell(
    name='AtomicCell',
    lattice_vectors=np.eye(3)*5.43*ureg.angstrom,
    periodic_boundary_conditions=[True,True,True]
)
model.cell.append(cell)

# set positions & per-atom states
model.positions = np.array([[0,0,0],[0.25,0.25,0.25]])*ureg.angstrom
from nomad_simulations.schema_packages.atoms_state import AtomsState
model.particle_states.append( AtomsState(chemical_symbol='Si', atomic_number=14) )
model.particle_states.append( AtomsState(chemical_symbol='Si', atomic_number=14) )

# convert to ASE
ase_atoms = model.to_ase_atoms(logger)

# build from an existing ASE.Atoms
model2 = ModelSystem()
model2.cell.append(cell)
model2.from_ase_atoms(ase_atoms, logger)

# normalize: auto‐fills type, dimensionality, symmetry, chemical_formula…
from nomad.datamodel import EntryArchive
archive = EntryArchive()
model.normalize(archive, logger)
```

## Hierarchical ModelSystems

You can nest systems to represent subgroups:

```python
ModelSystem (root)
├── sub_systems[0]: ModelSystem(branch_label="group_H2O", particle_indices=[0,1,2])
│    └── sub_systems[0]: ModelSystem(branch_label="H2O", particle_indices=[0,1,2])
└── sub_systems[1]: ModelSystem(branch_label="Cu")
     └── …
```

After normalization, each branch gets a branch_depth, and its composition_formula is set:

```python
root:             composition_formula = "group_H2O(1)Cu(1)"
group_H2O:        composition_formula = "H2O(3)"
H2O (leaf):       composition_formula = "H(1)O(2)"
Cu   (leaf):      composition_formula = "Cu(1)"
```