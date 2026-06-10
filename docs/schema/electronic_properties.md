# Electronic Structure Properties

**Purpose:** Electronic eigenvalues, band structures, DOS, band gaps, molecular orbitals, occupancies, and Fermi surfaces


## Relationship map


<div class="uml-diagram-card" markdown="1">

```mermaid
classDiagram
    class BaseElectronicEigenvalues
    class DOSProfile
    class ElectronicBandGap
    class ElectronicBandStructure
    class ElectronicDensityOfStates
    class ElectronicEigenvalues
    class Energy2
    class FermiSurface
    class MolecularOrbitals
    class Occupancy
    ElectronicEigenvalues <|-- ElectronicBandStructure
    DOSProfile <|-- ElectronicDensityOfStates
    BaseElectronicEigenvalues <|-- ElectronicEigenvalues
    ElectronicEigenvalues <|-- MolecularOrbitals
    DOSProfile *-- Energy2 : energies
    ElectronicDensityOfStates *-- DOSProfile : projected_dos
    ElectronicDensityOfStates *-- Energy2 : energies
    ElectronicEigenvalues *-- BaseElectronicEigenvalues : contributions
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="54" y1="8" x2="22" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M10 8 L22 2 L22 14 Z"/></svg><span>inheritance (is-a)</span></div>
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><path class="uml-legend__head uml-legend__head--filled" d="M10 8 L16 2 L22 8 L16 14 Z"/><line class="uml-legend__line" x1="22" y1="8" x2="52" y2="8"/></svg><span>composition (has-a)</span></div>
</div>

</div>


## Quantities by Key Sections

### `BaseElectronicEigenvalues`

| Section | Description | MetaInfo |
|---|---|---|
| `BaseElectronicEigenvalues` | A base section used to define basic quantities for the `ElectronicEigenvalues`  and `ElectronicBandStructure` properties. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.electronic_eigenvalues.BaseElectronicEigenvalues){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `n_levels` | m_int32(int32) | <details><summary>Number of energy levels per sampling point.</summary>Number of energy levels per sampling point.<br>In periodic systems these correspond to electronic bands; in molecular<br>calculations they correspond to (spin-resolved) molecular orbitals or<br>similar one-particle states.</details> |
| `value` | m_float64(float64) (shape: ['*', '*']) | Value of the electronic eigenvalues. |

### `ElectronicEigenvalues`

| Section | Description | MetaInfo |
|---|---|---|
| `ElectronicEigenvalues` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.electronic_eigenvalues.ElectronicEigenvalues){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `spin_channel` | m_int32(int32) | Spin channel of the corresponding electronic eigenvalues. It can take values of 0 or 1. |
| `occupation` | m_float64(float64) (shape: ['*', 'n_levels']) | <details><summary>Occupation of the electronic eigenvalues.</summary>Occupation of the electronic eigenvalues. This is a number depending whether the `spin_channel` has been set or not.<br>If `spin_channel` is set, then this number is between 0 and 1, where 0 means that the state is unoccupied and 1 means<br>that the state is fully occupied; if `spin_channel` is not set, then this number is between 0 and 2. The shape of<br>this quantity is defined as `[K.n_points, K.dimensionality, n_levels]`, where `K` is a `variable` which can<br>be `KMesh` or `KLinePath`, depending whether the simulation mapped the whole Brillouin zone or just a specific<br>path.</details> |
| `highest_occupied` | m_float64(float64) | Highest occupied electronic eigenvalue. Together with `lowest_unoccupied`, it defines the electronic band gap. |
| `lowest_unoccupied` | m_float64(float64) | Lowest unoccupied electronic eigenvalue. Together with `highest_occupied`, it defines the electronic band gap. |

### `ElectronicBandStructure`

| Section | Description | MetaInfo |
|---|---|---|
| `ElectronicBandStructure` | Accessible energies by the charges (electrons and holes) in the reciprocal space. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.band_structure.ElectronicBandStructure){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `reciprocal_cell` | QuantityReference | Reciprocal lattice vectors associated with the k-space sampling used for these eigenvalues, taken from the corresponding `KSpace` numerical settings. |

### `MolecularOrbitals`

| Section | Description | MetaInfo |
|---|---|---|
| `MolecularOrbitals` | Molecular-orbital eigenstates expressed in an atom-centered AO basis. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.molecular_orbitals.MolecularOrbitals){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `value` | m_float64(float64) (shape: ['n_levels']) | Orbital energies: eigenvalues of the effective one-particle Hamiltonian (Fock matrix for HF/DFT, natural-orbital energies for correlated methods). |
| `occupation` | m_float_bounded(float) (shape: ['n_levels']) | Occupation number for each molecular orbital. For a closed-shell restricted calculation the values are 0.0 or 2.0; for an unrestricted calculation (one section per spin channel) they are 0.0 or 1.0. |
| `n_ao` | m_int32(int32) | Number of atomic orbitals (size of the AO basis). |
| `basis_set_ref` | Reference | Reference to the atom-centered basis set used to expand these orbitals. |
| `coefficients` | HDF5Dataset | <details><summary>The AO→MO coefficient matrix **C**, such that</summary>The AO→MO coefficient matrix **C**, such that<br>ψ_i(r) = ∑_μ C[i,μ] φ_μ(r).<br>Row index i runs over MOs (n_levels), column index μ runs over AOs (n_ao).<br>Expected dataset shape: [n_levels, n_ao].</details> |
| `coefficients_im` | HDF5Dataset | <details><summary>Imaginary component of the AO→MO coefficient matrix.</summary>Imaginary component of the AO→MO coefficient matrix.<br>Combine with `coefficients` to obtain the full complex matrix:<br>C_complex = coefficients + 1j * coefficients_im<br>Omit for strictly real wave functions (non-relativistic calculations<br>without complex basis functions).<br>Expected dataset shape: [n_levels, n_ao].</details> |
| `role` | Enum (shape: ['n_levels']) | <details><summary>Role of each MO within a correlated calculation or active-space protocol:</summary>Role of each MO within a correlated calculation or active-space protocol:<br>* core     : energy-frozen doubly-occupied<br>* inactive : doubly-occupied but variationally optimised<br>* active   : part of the active space<br>* virtual  : unoccupied (correlated) orbital<br>* deleted  : pruned for technical reasons</details> |
| `symmetry` | m_str(str) (shape: ['n_levels']) | Symmetry label of each MO in the molecule's point group (e.g. a₁, b₂u, π_g). Leave empty for systems with no detected symmetry. |
| `kind` | Enum | <details><summary>Classification of the orbital set:</summary>Classification of the orbital set:<br>* canonical  : standard SCF eigenfunctions<br>* natural    : eigenfunctions of the 1-RDM<br>* localized  : after a localization transform (Boys, Pipek-Mezey, …)<br>* hybrid     : post-HF orbitals, e.g. CASSCF</details> |

### `ElectronicBandGap`

| Section | Description | MetaInfo |
|---|---|---|
| `ElectronicBandGap` | Energy difference between the highest occupied electronic state and the lowest unoccupied electronic state. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.band_gap.ElectronicBandGap){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `type` | Enum | Type categorization of the electronic band gap. This quantity is directly related with `momentum_transfer` as by definition, the electronic band gap is `'direct'` for zero momentum transfer (or if `momentum_transfer` is `None`) and `'indirect'` for finite momentum transfer. |
| `momentum_transfer` | m_float64(float64) (shape: [2, 3]) | <details><summary>If the electronic band gap is `'indirect'`, the reciprocal momentum transfer for...</summary>If the electronic band gap is `'indirect'`, the reciprocal momentum transfer for which the band gap is defined<br>in units of the `reciprocal_lattice_vectors`. The initial and final momentum 3D vectors are given in the first<br>and second element. Example, the momentum transfer in bulk Si2 happens between the Γ and the (approximately)<br>X points in the Brillouin zone; thus:<br>`momentum_transfer = [[0, 0, 0], [0.5, 0.5, 0]]`.<br>Note: this quantity only refers to scalar `value`, not to arrays of `value`.</details> |
| `spin_channel` | m_int32(int32) | Spin channel of the corresponding electronic band gap. It can take values of 0 or 1. |
| `value` | m_float_bounded(float) | The value of the electronic band gap. This value must be positive. |

### `DOSProfile`

| Section | Description | MetaInfo |
|---|---|---|
| `DOSProfile` | A base section used to define the `value` of the `ElectronicDensityOfState` property. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.spectral_profile.DOSProfile){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `value` | m_float_bounded(float) (shape: ['*']) | The value of the electronic DOS. Must be positive. |

### `ElectronicDensityOfStates`

| Section | Description | MetaInfo |
|---|---|---|
| `ElectronicDensityOfStates` | Number of electronic states accessible for the charges per energy and per volume. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.spectral_profile.ElectronicDensityOfStates){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `spin_channel` | m_int32(int32) | Spin channel of the corresponding electronic DOS. It can take values of 0 or 1. |
| `energies_origin` | m_float64(float64) | Energy level denoting the origin along the energy axis, used for comparison and visualization. It is defined as the `ElectronicEigenvalues.highest_occupied_energy`. |
| `normalization_factor` | m_float64(float64) | Normalization factor for electronic DOS to get a cell-independent intensive DOS. The cell-independent intensive DOS is as the integral from the lowest (most negative) energy to the Fermi level for a neutrally charged system (i.e., the sum of `AtomsState.charge` is zero). |

### `Occupancy`

| Section | Description | MetaInfo |
|---|---|---|
| `Occupancy` | Electrons occupancy of an atom per orbital and spin. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.electronic_eigenvalues.Occupancy){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `orbitals_state_ref` | Reference | Reference to the `ElectronicState` section in which the occupancy is calculated. This can reference individual orbitals, orbital manifolds, or hybrid/molecular orbitals. The parent AtomsState can be accessed via `orbitals_state_ref.get_parent_entity()`. |
| `spin_channel` | m_int32(int32) | Spin channel of the corresponding electronic property. It can take values of 0 and 1. |
| `value` | m_float64(float64) | <details><summary>Value of the electronic occupancy for the orbital defined by `orbitals_state_ref`.</summary>Value of the electronic occupancy for the orbital defined by `orbitals_state_ref`.<br>If `spin_channel` is set, then this number is between 0 and 1, where 0 means that<br>the state is unoccupied and 1 means that the state is fully occupied; if `spin_channel`<br>is not set, then this number is between 0 and 2.</details> |

### `FermiSurface`

| Section | Description | MetaInfo |
|---|---|---|
| `FermiSurface` | Energy boundary in reciprocal space that separates the filled and empty electronic states in a metal. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.fermi_surface.FermiSurface){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `n_bands` | m_int32(int32) | Number of bands / eigenvalues. |


