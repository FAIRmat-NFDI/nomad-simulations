# Model Methods

**Purpose:** Complete ModelMethod tree: electronic structure methods and their hierarchy

**In scope:**

Method inheritance hierarchy: BaseModelMethod → ModelMethod → ModelMethodElectronic

DFT: Jacobs ladder, XC functionals, exact exchange, van der Waals

Tight-binding (TB): DFTB, xTB, Wannier, Slater-Koster

Excited states: ExcitedStateMethodology → GW, BSE

Screening for many-body methods

CoreHoleSpectra for X-ray spectroscopy

DMFT for strongly correlated systems

Method contributions and references between methods

**Out of scope:**

Numerical settings like meshes and basis sets (see numerical_settings)

Output properties computed by these methods (see output verticals)

## Relationship map

!!! tip "Interactive Diagram"
    **Click on the diagram below to zoom in.** Click again to zoom out.

    The diagram shows the relationships between the key sections in this vertical domain.


![model_method_0 diagram](../assets/diagrams/model_method_0.svg){: style="width: 80%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `BaseModelMethod` | A base section used to define the abstract class of a Hamiltonian section. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.BaseModelMethod){:target="_blank"} |
| `ModelMethod` | A base section containing the mathematical model parameters. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.ModelMethod){:target="_blank"} |
| `ModelMethodElectronic` | A base section used to define the parameters of a model Hamiltonian used in electronic structure calculations (TB, DFT, GW, BSE, DMFT, etc). | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.ModelMethodElectronic){:target="_blank"} |
| `DFT` | A base section used to define the parameters used in a density functional theory (DFT) calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.DFT){:target="_blank"} |
| `XCFunctional` | A base section used to define the parameters of an exchange or correlation functional. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.XCFunctional){:target="_blank"} |
| `TB` | A base section containing the parameters pertaining to a tight-binding (TB) model calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.TB){:target="_blank"} |
| `Wannier` | A base section used to define the parameters used in a Wannier tight-binding fitting. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.Wannier){:target="_blank"} |
| `SlaterKoster` | A base section used to define the parameters used in a Slater-Koster tight-binding fitting. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.SlaterKoster){:target="_blank"} |
| `SlaterKosterBond` | A base section used to define the Slater-Koster bond information betwee two orbitals. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.SlaterKosterBond){:target="_blank"} |
| `xTB` | A base section used to define the parameters used in an extended tight-binding (xTB) calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.xTB){:target="_blank"} |
| `ExcitedStateMethodology` | A base section used to define the parameters typical of excited-state calculations. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.ExcitedStateMethodology){:target="_blank"} |
| `Screening` | A base section used to define the parameters that define the calculation of screening. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.Screening){:target="_blank"} |
| `GW` | A base section used to define the parameters of a GW calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.GW){:target="_blank"} |
| `BSE` | A base section used to define the parameters of a BSE calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.BSE){:target="_blank"} |
| `CoreHoleSpectra` | A base section used to define the parameters used in a core-hole spectra calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.CoreHoleSpectra){:target="_blank"} |
| `Photon` | A base section used to define parameters of a photon, typically used for optical responses. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.Photon){:target="_blank"} |
| `DMFT` | A base section used to define the parameters of a DMFT calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.DMFT){:target="_blank"} |


## Micro-examples

=== "YAML"

    ```yaml
    BaseModelMethod:
      name:
      - null
      type:
      - null
      external_reference:
      - null
      numerical_settings:
      - {}
    ModelMethod:
      contributions:
      - {}
    ModelMethodElectronic:
      is_spin_polarized:
      - null
      relativity_method:
      - null
    DFT:
      jacobs_ladder:
      - null
      exact_exchange_mixing_factor:
      - null
      self_interaction_correction_method:
      - null
      van_der_waals_correction:
      - null
      xc_functionals:
      - {}
    XCFunctional:
      libxc_name:
      - null
      name:
      - null
      weight:
      - null
    TB:
      type: unavailable
      n_orbitals_per_atom:
      - null
      n_atoms_per_unit_cell:
      - null
      n_total_orbitals:
      - null
      orbitals_ref:
      - null
    Wannier:
      is_maximally_localized:
      - null
      localization_type:
      - null
      n_bloch_bands:
      - null
      energy_window_outer:
      - null
      energy_window_inner:
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
    xTB: {}
    ExcitedStateMethodology:
      n_states:
      - null
      n_empty_states:
      - null
      broadening:
      - null
    Screening:
      dielectric_infinity:
      - null
    GW:
      type:
      - null
      analytical_continuation:
      - null
      interval_qp_corrections:
      - null
      screening_ref:
      - null
    BSE:
      type:
      - null
      solver:
      - null
      screening_ref:
      - null
    CoreHoleSpectra:
      type:
      - null
      edge:
      - null
      core_hole_ref:
      - null
      excited_state_method_ref:
      - null
    Photon:
      multipole_type:
      - null
      polarization:
      - null
      energy:
      - null
      momentum_transfer:
      - null
    DMFT:
      impurity_solver:
      - null
      n_impurities:
      - null
      n_orbitals:
      - null
      orbitals_ref:
      - null
      n_electrons:
      - null
      inverse_temperature:
      - null
      magnetic_state:
      - null
    ```