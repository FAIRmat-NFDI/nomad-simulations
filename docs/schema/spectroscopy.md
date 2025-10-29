# Spectroscopy & Excitations

**Purpose.** Excited-state methods and spectra.**In scope:** BSE/GW artifacts, response functions, quasiparticles**Out of scope:** ground-state-only properties
## Relationship map

```mermaid
classDiagram
    class AbsorptionSpectrum
    class BSE
    class DFTGWModel
    class DFTGWResults
    class DFTGWWorkflow
    class ElectronicGreensFunction
    class ElectronicSelfEnergy
    class Outputs
    class QuasiparticleWeight
    class Screening
    class XASSpectrum
    Outputs --> AbsorptionSpectrum : absorption_spectra
    Outputs --> ElectronicGreensFunction : electronic_greens_functions
    Outputs --> ElectronicSelfEnergy : electronic_self_energies
    Outputs --> QuasiparticleWeight : quasiparticle_weights
    Outputs --> XASSpectrum : xas_spectra
    XASSpectrum --> AbsorptionSpectrum : exafs_spectrum
    XASSpectrum --> AbsorptionSpectrum : xanes_spectrum
```


## Key sections- `AbsorptionSpectrum` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `XASSpectrum` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `BSE` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `Screening` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `ElectronicGreensFunction` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `ElectronicSelfEnergy` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `QuasiparticleWeight` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `DFTGWModel` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `DFTGWResults` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `DFTGWWorkflow` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)
## Micro-examples

=== "YAML"
```yaml
AbsorptionSpectrum:
  axis:
  - null
XASSpectrum:
  xanes_spectrum: {}
  exafs_spectrum: {}
BSE:
  type:
  - null
  solver:
  - null
  screening_ref:
  - null
Screening:
  dielectric_infinity:
  - null
ElectronicGreensFunction:
  value:
  - null
ElectronicSelfEnergy:
  value:
  - null
QuasiparticleWeight:
  system_correlation_strengths:
  - null
  n_atoms:
  - null
  atoms_state_ref:
  - null
  n_correlated_orbitals:
  - null
  correlated_orbitals_ref:
  - null
  spin_channel:
  - null
  value:
  - null
DFTGWModel: {}
DFTGWResults: {}
DFTGWWorkflow: {}
