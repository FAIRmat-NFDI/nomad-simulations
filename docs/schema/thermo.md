# Thermodynamics

**Purpose.** Thermodynamic state functions and models.**In scope:** state functions, derived thermodynamic curves**Out of scope:** MD raw trajectories (see Results)
## Relationship map

```mermaid
classDiagram
    class Enthalpy
    class Entropy
    class GibbsFreeEnergy
    class HeatCapacity
    class HelmholtzFreeEnergy
    class InternalEnergy
    class Thermodynamics
    class ThermodynamicsModel
    class ThermodynamicsResults
```


## Key sections- `Thermodynamics` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `ThermodynamicsModel` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `ThermodynamicsResults` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `HeatCapacity` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `Entropy` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `HelmholtzFreeEnergy` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `GibbsFreeEnergy` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `Enthalpy` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `InternalEnergy` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)
## Micro-examples

=== "YAML"
```yaml
Thermodynamics: {}
ThermodynamicsModel: {}
ThermodynamicsResults:
  n_values:
  - null
  temperature:
  - null
  pressure:
  - null
HeatCapacity:
  value:
  - null
Entropy:
  value:
  - null
HelmholtzFreeEnergy: {}
GibbsFreeEnergy: {}
Enthalpy: {}
InternalEnergy: {}
