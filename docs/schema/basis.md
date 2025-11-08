# Basis & Orbitals

**Purpose.** Representations used to expand wavefunctions or Hamiltonians.
**In scope:** plane wave parameters, APW/APW+lo, localized atomic basis, tight-binding tables
**Out of scope:** results derived from the basis (e.g., DOS)

## Relationship map

!!! tip "Interactive Diagram"
    **Click on the diagram below to zoom in.** Click again to zoom out.
    
    The diagram shows the relationships between the key sections in this vertical domain.


![basis_0 diagram](../assets/diagrams/basis_0.svg){: style="width: 80%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `PlaneWaveBasisSet` | Basis set over a reciprocal mesh, where each point $k_n$ represents a planar-wave basis function $rac{1}{\sqrt{\omega}} e^{i k_n r}$. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.basis_set.PlaneWaveBasisSet){:target="_blank"} |
| `AtomCenteredBasisSet` | Defines an **atom-centered basis set** for quantum chemistry calculations. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.basis_set.AtomCenteredBasisSet){:target="_blank"} |
| `APWPlaneWaveBasisSet` | A `PlaneWaveBasisSet` specialized to the APW use case. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.basis_set.APWPlaneWaveBasisSet){:target="_blank"} |
| `APWLocalOrbital` | Implementation of `APWWavefunction` capturing a local orbital extending a foundational APW basis set. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.basis_set.APWLocalOrbital){:target="_blank"} |
| `APWOrbital` | Implementation of `APWWavefunction` capturing the foundational (S)(L)APW basis sets, all of the form $\sum_{lm} \left[ \sum_o c_{lmo} rac{\partial}{\partial r}u_l(r, \epsilon_l) 
ight] Y_lm$. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.basis_set.APWOrbital){:target="_blank"} |
| `AtomCenteredFunction` | Specifies a single contracted basis function in an atom-centered basis set. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.basis_set.AtomCenteredFunction){:target="_blank"} |
| `SlaterKoster` | A base section used to define the parameters used in a Slater-Koster tight-binding fitting. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.SlaterKoster){:target="_blank"} |
| `SlaterKosterBond` | A base section used to define the Slater-Koster bond information betwee two orbitals. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.SlaterKosterBond){:target="_blank"} |


## Micro-examples

=== "YAML"

    ```yaml
    PlaneWaveBasisSet:
      cutoff_energy:
      - null
      cutoff_radius:
      - null
    AtomCenteredBasisSet:
      basis_set:
      - null
      type:
      - null
      role:
      - null
      ao_ordering_convention: Gaussian
      ao_custom_order:
      - null
      n_total_basis_functions:
      - null
      functional_compositions:
      - {}
      atomic_orbitals: {}
      ecps:
      - {}
    APWPlaneWaveBasisSet:
      cutoff_fractional:
      - null
    APWLocalOrbital: {}
    APWOrbital:
      type:
      - null
    AtomCenteredFunction:
      angular_type: spherical
      function_type:
      - null
      angular_momentum:
      - null
      r_power:
      - null
      shell_normalization:
      - null
      n_primitive:
      - null
      exponents:
      - null
      contraction_coefficients:
      - null
      primitive_factor:
      - null
      point_charge:
      - null
    SlaterKoster:
      bonds:
      - {}
      overlaps:
      - {}
    SlaterKosterBond:
      orbital_1:
      - null
      orbital_2:
      - null
      bravais_vector:
      - 0
      - 0
      - 0
      name:
      - null
      integral_value:
      - null
    ```