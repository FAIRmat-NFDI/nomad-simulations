# Many-Body Properties

**Purpose:** Green's functions, self-energies, hybridization, quasiparticle weights, hopping matrices

**In scope:**

- Green's function base class and electronic specialization
- Self-energies from GW and DMFT
- Hybridization functions for impurity problems
- Quasiparticle renormalization weights
- Hopping matrices from tight-binding
- Crystal field splittings in correlated systems

## Relationship map


```mermaid
classDiagram
    class BaseGreensFunction
    class CrystalFieldSplitting
    class ElectronicGreensFunction
    class ElectronicSelfEnergy
    class Frequency
    class HoppingMatrix
    class HybridizationFunction
    class ImaginaryTime
    class MatsubaraFrequency
    class QuasiparticleWeight
    class Time
    class WignerSeitz
    BaseGreensFunction <|-- ElectronicGreensFunction
    BaseGreensFunction <|-- ElectronicSelfEnergy
    BaseGreensFunction <|-- HybridizationFunction
    BaseGreensFunction --> Frequency : real_frequency
    BaseGreensFunction --> ImaginaryTime : imaginary_time
    BaseGreensFunction --> MatsubaraFrequency : matsubara_frequency
    BaseGreensFunction --> Time : time
    BaseGreensFunction --> WignerSeitz : wigner_seitz
```

**Legend**

<div style="display:flex; align-items:center; gap:8px; margin:3px 0;"><svg width="56" height="16" aria-hidden="true"><line x1="48" y1="8" x2="18" y2="8" stroke="currentColor" stroke-width="1.8"/><polygon points="18,8 26,4 26,12" fill="white" stroke="currentColor" stroke-width="1.8"/></svg><code>Parent &lt;|-- Child</code> inheritance (Child extends Parent)</div>
<div style="display:flex; align-items:center; gap:8px; margin:3px 0;"><svg width="56" height="16" aria-hidden="true"><line x1="8" y1="8" x2="38" y2="8" stroke="currentColor" stroke-width="1.8"/><polygon points="46,8 38,4 38,12" fill="currentColor"/></svg><code>Owner --&gt; SubSection</code> containment/subsection</div>


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `BaseGreensFunction` | A base class used to define shared commonalities between Green's function-related properties. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.greens_function.BaseGreensFunction){:target="_blank"} |
| `ElectronicGreensFunction` | Charge-charge correlation functions. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.greens_function.ElectronicGreensFunction){:target="_blank"} |
| `ElectronicSelfEnergy` | Corrections to the energy of an electron due to its interactions with its environment. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.greens_function.ElectronicSelfEnergy){:target="_blank"} |
| `HybridizationFunction` | Dynamical hopping of the electrons in a lattice in and out of the reservoir or bath. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.greens_function.HybridizationFunction){:target="_blank"} |
| `QuasiparticleWeight` | Renormalization of the electronic mass due to the interactions with the environment. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.greens_function.QuasiparticleWeight){:target="_blank"} |
| `HoppingMatrix` | Transition probability between two atomic orbitals in a tight-binding model. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.hopping_matrix.HoppingMatrix){:target="_blank"} |
| `CrystalFieldSplitting` | Energy difference between the degenerated orbitals of an ion in a crystal field environment. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.hopping_matrix.CrystalFieldSplitting){:target="_blank"} |


## Quantities by section

### `BaseGreensFunction`

| Quantity | Type | Description |
|---|---|---|
| `n_atoms` | m_int32(int32) | Number of atoms involved in the correlations effect and used for the matrix representation of the property. Can be derived from entity_ref if needed. |
| `entity_ref` | <nomad.metainfo.metainfo.Reference object at 0x7105cf494e60> | Reference to the `ElectronicState` section describing the correlated orbitals for which the Green's function properties are calculated. The parent AtomsState can be accessed via `entity_ref.get_parent_entity()`. |
| `spin_channel` | m_int32(int32) | Spin channel of the corresponding electronic property. It can take values of 0 and 1. |
| `local_model_type` | Enum | <details><summary>Type of Green's function calculated from the mapping of the local Hubbard-Kanamo...</summary>Type of Green's function calculated from the mapping of the local Hubbard-Kanamori model<br>into the Anderson impurity model.<br>The `impurity` Green's function describe the electronic correlations for the impurity, and it<br>is a local function. The `lattice` Green's function includes the coupling to the lattice<br>and hence it is a non-local function. In DMFT, the `lattice` term is approximated to be the<br>`impurity` one, so that these simulations are converged if both types of the local<br>part of the `lattice` Green's function coincides with the `impurity` Green's function.</details> |
| `space_id` | Enum | <details><summary>String used to identify the space in which the Green's function property is represented.</summary>String used to identify the space in which the Green's function property is represented. The spaces are:<br>\| `space_id` \| variable type \|<br>\| ------ \| ------ \|<br>\| 'r' \| WignerSeitz \|<br>\| 'rt' \| WignerSeitz + Time \|<br>\| 'rw' \| WignerSeitz + Frequency \|<br>\| 'rit' \| WignerSeitz + ImaginaryTime \|<br>\| 'riw' \| WignerSeitz + MatsubaraFrequency \|<br>\| 'k' \| KMesh \|<br>\| 'kt' \| KMesh + Time \|<br>\| 'kw' \| KMesh + Frequency \|<br>\| 'kit' \| KMesh + ImaginaryTime \|<br>\| 'kiw' \| KMesh + MatsubaraFrequency \|<br>\| 't' \| Time \|<br>\| 'it' \| Frequency \|<br>\| 'w' \| ImaginaryTime \|<br>\| 'iw' \| MatsubaraFrequency \|</details> |

### `ElectronicGreensFunction`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_complex128(complex128) | Value of the electronic Green's function matrix. |

### `ElectronicSelfEnergy`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_complex128(complex128) | Value of the electronic self-energy matrix. |

### `HybridizationFunction`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_complex128(complex128) | Value of the electronic hybridization function. |

### `QuasiparticleWeight`

| Quantity | Type | Description |
|---|---|---|
| `system_correlation_strengths` | Enum | <details><summary>String used to identify the type of system based on the strength of the electron-electron interactions.</summary>String used to identify the type of system based on the strength of the electron-electron interactions.<br>\| `type` \| Description \|<br>\| ------ \| ------ \|<br>\| 'non-correlated metal' \| All `value` are above 0.7. Renormalization effects are negligible. \|<br>\| 'strongly-correlated metal' \| All `value` are below 0.4 and above 0. Renormalization effects are important. \|<br>\| 'OSMI' \| Orbital-selective Mott insulator: some orbitals have a zero `value` while others a finite one. \|<br>\| 'Mott insulator' \| All `value` are 0.0. Mott insulator state. \|</details> |
| `n_atoms` | m_int32(int32) | Number of atoms involved in the correlations effect and used for the matrix representation of the quasiparticle weight. Can be derived from entity_ref if needed. |
| `n_correlated_orbitals` | m_int32(int32) | Number of orbitals involved in the correlations effect and used for the matrix representation of the quasiparticle weight. |
| `entity_ref` | <nomad.metainfo.metainfo.Reference object at 0x7105cf6270e0> | Reference to the `ElectronicState` section describing the correlated orbitals for which the quasiparticle weight is calculated. The parent AtomsState can be accessed via `entity_ref.get_parent_entity()`. |
| `spin_channel` | m_int32(int32) | Spin channel of the corresponding electronic property. It can take values of 0 and 1. |
| `value` | m_float_bounded(float) (shape: ['*']) | Value of the quasi-particle weight matrices. Must be between 0 and 1. |

### `HoppingMatrix`

| Quantity | Type | Description |
|---|---|---|
| `n_orbitals` | m_int32(int32) | Number of orbitals in the tight-binding model. The `entity_ref` reference is used to refer to the `ElectronicState` section, which navigates to the relevant basis orbitals (e.g., `SphericalSymmetryState`). |
| `degeneracy_factors` | m_int32(int32) (shape: ['*']) | Degeneracy of each Wigner-Seitz point. |
| `value` | m_complex128(complex128) | Value of the hopping matrix in joules. The elements are complex numbers defined for each Wigner-Seitz point and each pair of orbitals. Note this contains also the onsite values, i.e., it includes the Wigner-Seitz point (0, 0, 0), hence the `CrystalFieldSplitting` values. |

### `CrystalFieldSplitting`

| Quantity | Type | Description |
|---|---|---|
| `n_orbitals` | m_int32(int32) | Number of orbitals in the tight-binding model. The `entity_ref` reference is used to refer to the `ElectronicState` section, which navigates to the relevant basis orbitals (e.g., `SphericalSymmetryState`). |
| `value` | m_float64(float64) | Value of the crystal field splittings in joules. This is the intra-orbital local contribution, i.e., the same orbital at the same Wigner-Seitz point (0, 0, 0). |

