# Methods & Parameters

**Purpose.** Code-agnostic method choices and numerical controls that drive reproducibility.
**In scope:** electronic-structure family, XC selection, smearing, numerical cutoffs/settings
**Out of scope:** runtime logs, post-processed properties

## Relationship map

!!! tip "Interactive Diagram"
    **Click on the diagram below to zoom in.** Click again to zoom out.
    
    The diagram shows the relationships between the key sections in this vertical domain.


![methods_0 diagram](../assets/diagrams/methods_0.svg){: style="width: 80%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `ModelMethod` | A base section containing the mathematical model parameters. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.ModelMethod){:target="_blank"} |
| `ModelMethodElectronic` | A base section used to define the parameters of a model Hamiltonian used in electronic structure calculations (TB, DFT, GW, BSE, DMFT, etc). | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.ModelMethodElectronic){:target="_blank"} |
| `DFT` | A base section used to define the parameters used in a density functional theory (DFT) calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.DFT){:target="_blank"} |
| `TB` | A base section containing the parameters pertaining to a tight-binding (TB) model calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.TB){:target="_blank"} |
| `DMFT` | A base section used to define the parameters of a DMFT calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.DMFT){:target="_blank"} |
| `GW` | A base section used to define the parameters of a GW calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.GW){:target="_blank"} |
| `XCFunctional` | A base section used to define the parameters of an exchange or correlation functional. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.XCFunctional){:target="_blank"} |
| `NumericalSettings` | A base section used to define the numerical settings used in a simulation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.numerical_settings.NumericalSettings){:target="_blank"} |
| `Smearing` | Section specifying the smearing of the occupation numbers to either simulate temperature effects or improve SCF convergence. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.numerical_settings.Smearing){:target="_blank"} |
| `Program` | A base section used to specify a well-defined program used for computation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.general.Program){:target="_blank"} |


## Micro-examples

=== "YAML"

    ```yaml
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
    GW:
      type:
      - null
      analytical_continuation:
      - null
      interval_qp_corrections:
      - null
      screening_ref:
      - null
    XCFunctional:
      libxc_name:
      - null
      name:
      - null
      weight:
      - null
    NumericalSettings:
      name:
      - null
    Smearing:
      name:
      - null
    Program:
      name:
      - null
      version:
      - null
      link:
      - null
      version_internal:
      - null
      subroutine_name_internal:
      - null
      compilation_host:
      - null
    ```