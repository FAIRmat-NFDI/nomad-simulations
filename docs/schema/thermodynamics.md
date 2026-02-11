# Thermodynamic Properties

**Purpose:** Energies, forces, pressure, temperature, and thermodynamic state functions

**In scope:**

- Energy hierarchy: BaseEnergy → specific energy types
- Free energies: Gibbs, Helmholtz
- Force hierarchy: BaseForce → TotalForce
- Thermodynamic state variables: pressure, volume, temperature
- Entropy and heat capacities
- Virial tensor for stress calculations
- Hessian matrices for phonon calculations

**Out of scope:**

- Electronic structure properties
- Spectroscopic properties

## Relationship map


```mermaid
classDiagram
    class BaseEnergy
    class BaseForce
    class ChemicalPotential
    class Enthalpy
    class Entropy
    class GibbsFreeEnergy
    class Heat
    class HeatCapacity
    class HelmholtzFreeEnergy
    class Hessian
    class InternalEnergy
    class KineticEnergy
    class MassDensity
    class PotentialEnergy
    class Pressure
    class Temperature
    class TotalEnergy
    class TotalForce
    class VirialTensor
    class Volume
    class Work
    BaseEnergy <|-- ChemicalPotential
    BaseEnergy <|-- Enthalpy
    BaseEnergy <|-- GibbsFreeEnergy
    BaseEnergy <|-- Heat
    BaseEnergy <|-- HelmholtzFreeEnergy
    BaseEnergy <|-- InternalEnergy
    BaseEnergy <|-- KineticEnergy
    BaseEnergy <|-- PotentialEnergy
    BaseEnergy <|-- TotalEnergy
    BaseForce <|-- TotalForce
    BaseEnergy <|-- VirialTensor
    BaseEnergy <|-- Work
    TotalEnergy --> BaseEnergy : contributions
    TotalForce --> BaseForce : contributions
```

<div style="font-size: 0.9em; color: #666; margin-top: 8px; margin-bottom: 8px;">
<b>Legend:</b>
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="20" y1="6" x2="4" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="4,6 8,3 8,9" fill="none" stroke="currentColor" stroke-width="1.5"/></svg> inheritance ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> containment ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2,2"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> reference
</div>


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `BaseEnergy` | Abstract class used to define a common `value` quantity with the appropriate units for different types of energies, which avoids repeating the definit... | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.energies.BaseEnergy){:target="_blank"} |
| `TotalEnergy` | The total energy of a system. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.energies.TotalEnergy){:target="_blank"} |
| `KineticEnergy` | Physical property section describing the kinetic energy of a (sub)system. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.energies.KineticEnergy){:target="_blank"} |
| `PotentialEnergy` | Physical property section describing the potential energy of a (sub)system. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.energies.PotentialEnergy){:target="_blank"} |
| `Heat` | The transfer of thermal energy **into** a system. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.Heat){:target="_blank"} |
| `Work` | The energy transferred to a system by means of force applied over a distance. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.Work){:target="_blank"} |
| `InternalEnergy` | The total energy contained within a system, encompassing both kinetic and potential energies of the particles. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.InternalEnergy){:target="_blank"} |
| `Enthalpy` | The total heat content of a system, defined as 'InternalEnergy' + 'Pressure' * 'Volume'. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.Enthalpy){:target="_blank"} |
| `GibbsFreeEnergy` | The energy available to do work in a system at constant temperature and pressure, given by `Enthalpy` - `Temperature` * `Entropy`. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.GibbsFreeEnergy){:target="_blank"} |
| `HelmholtzFreeEnergy` | The energy available to do work in a system at constant volume and temperature, given by `InternalEnergy` - `Temperature` * `Entropy`. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.HelmholtzFreeEnergy){:target="_blank"} |
| `ChemicalPotential` | Free energy cost of adding or extracting a particle from a thermodynamic system. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.ChemicalPotential){:target="_blank"} |
| `VirialTensor` | A measure of the distribution of internal forces and the overall stress within a system of particles. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.VirialTensor){:target="_blank"} |
| `BaseForce` | Base class used to define a common `value` quantity with the appropriate units for different types of forces, which avoids repeating the definitions f... | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.forces.BaseForce){:target="_blank"} |
| `TotalForce` | The total force of a system. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.forces.TotalForce){:target="_blank"} |
| `Pressure` | The force exerted per unit area by gas particles as they collide with the walls of their container. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.Pressure){:target="_blank"} |
| `Volume` | the amount of three-dimensional space that a substance or material occupies. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.Volume){:target="_blank"} |
| `Temperature` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.variables.Temperature){:target="_blank"} |
| `Entropy` | A measure of the disorder or randomness in a system. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.Entropy){:target="_blank"} |
| `HeatCapacity` | Amount of heat to be supplied to a material to produce a unit change in its temperature. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.HeatCapacity){:target="_blank"} |
| `MassDensity` | Mass per unit volume of a material. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.MassDensity){:target="_blank"} |
| `Hessian` | A square matrix of second-order partial derivatives of a potential energy function, describing the local curvature of the energy surface. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.thermodynamics.Hessian){:target="_blank"} |


## Quantities by section

### `BaseEnergy`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_float64(float64) | No description available. |

### `TotalEnergy`

*This section has no direct quantities.*

### `KineticEnergy`

*This section has no direct quantities.*

### `PotentialEnergy`

*This section has no direct quantities.*

### `Heat`

*This section has no direct quantities.*

### `Work`

*This section has no direct quantities.*

### `InternalEnergy`

*This section has no direct quantities.*

### `Enthalpy`

*This section has no direct quantities.*

### `GibbsFreeEnergy`

*This section has no direct quantities.*

### `HelmholtzFreeEnergy`

*This section has no direct quantities.*

### `ChemicalPotential`

| Quantity | Type | Description |
|---|---|---|
| `temperature` | m_float64(float64) | Temperature at which the chemical potential is calculated. Essential for finite-temperature calculations. |
| `particle_number` | m_float64(float64) | Number of particles (or particle density) for which the chemical potential applies. Can represent electron number, atom number, or other relevant particle count. |
| `fermi_energy` | m_float64(float64) | Fermi energy at T=0K, used as reference for finite-temperature chemical potential. At T=0, the chemical potential equals the Fermi energy. |
| `type` | m_str(str) | Type of chemical potential calculation. Examples: 'electronic', 'atomic', 'ionic', 'molecular'. Helps identify what kind of particles this applies to. |

### `VirialTensor`

*This section has no direct quantities.*

### `BaseForce`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_float64(float64) (shape: ['*', '*']) | No description available. |

### `TotalForce`

*This section has no direct quantities.*

### `Pressure`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_float64(float64) | No description available. |

### `Volume`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_float64(float64) | No description available. |

### `Temperature`

| Quantity | Type | Description |
|---|---|---|
| `points` | m_float64(float64) (shape: ['n_points']) | Points in which the temperature is discretized. |

### `Entropy`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_float64(float64) | No description available. |

### `HeatCapacity`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_float64(float64) | No description available. |

### `MassDensity`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_float64(float64) | No description available. |

### `Hessian`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_float64(float64) | No description available. |

