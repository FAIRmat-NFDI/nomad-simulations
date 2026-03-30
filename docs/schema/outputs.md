# Outputs

**Purpose:** Base output structure and common property definitions

**In scope:**

- Outputs section that references ModelSystem and ModelMethod
- SCFSteps with scf_steps quantities for SCF iteration history
- PhysicalProperty base class for all computed properties
- Property contributions and derivations
- SCF convergence data (energy deltas, density changes, etc.)


## Relationship map


<div class="uml-diagram-card" markdown="1">

```mermaid
classDiagram
    class AbsorptionSpectrum
    class ChemicalPotential
    class CrystalFieldSplitting
    class ElectronicBandGap
    class ElectronicBandStructure
    class ElectronicDensityOfStates
    class ElectronicEigenvalues
    class ElectronicGreensFunction
    class ElectronicSelfEnergy
    class FermiSurface
    class HoppingMatrix
    class HybridizationFunction
    class KineticEnergy
    class Occupancy
    class Outputs
    class Permittivity
    class PhysicalProperty
    class PotentialEnergy
    class QuasiparticleWeight
    class RadiusOfGyration
    class SCFSteps
    class Temperature
    class TotalEnergy
    class TotalForce
    class XASSpectrum
    Outputs *-- AbsorptionSpectrum : absorption_spectra
    Outputs *-- ChemicalPotential : chemical_potentials
    Outputs *-- CrystalFieldSplitting : crystal_field_splittings
    Outputs *-- ElectronicBandGap : electronic_band_gaps
    Outputs *-- ElectronicBandStructure : electronic_band_structures
    Outputs *-- ElectronicDensityOfStates : electronic_dos
    Outputs *-- ElectronicEigenvalues : electronic_eigenvalues
    Outputs *-- ElectronicGreensFunction : electronic_greens_functions
    Outputs *-- ElectronicSelfEnergy : electronic_self_energies
    Outputs *-- FermiSurface : fermi_surfaces
    Outputs *-- HoppingMatrix : hopping_matrices
    Outputs *-- HybridizationFunction : hybridization_functions
    Outputs *-- KineticEnergy : kinetic_energies
    Outputs *-- Occupancy : occupancies
    Outputs *-- Permittivity : permittivities
    Outputs *-- PotentialEnergy : potential_energies
    Outputs *-- QuasiparticleWeight : quasiparticle_weights
    Outputs *-- RadiusOfGyration : radii_of_gyration
    Outputs *-- SCFSteps : scf_steps
    Outputs *-- Temperature : temperatures
    Outputs *-- TotalEnergy : total_energies
    Outputs *-- TotalForce : total_forces
    Outputs *-- XASSpectrum : xas_spectra
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><path class="uml-legend__head uml-legend__head--filled" d="M10 8 L16 2 L22 8 L16 14 Z"/><line class="uml-legend__line" x1="22" y1="8" x2="52" y2="8"/></svg><span>composition (has-a)</span></div>
</div>

</div>


## Quantities by Key Sections

### `Outputs`

| Section | Description | MetaInfo |
|---|---|---|
| `Outputs` | Output properties of a simulation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.outputs.Outputs){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `model_system_ref` | Reference | Reference to the `ModelSystem` section in which the output physical properties were calculated. |
| `model_method_ref` | Reference | Reference to the `ModelMethod` section containing the details of the mathematical model with which the output physical properties were calculated. |

### `SCFSteps`

| Section | Description | MetaInfo |
|---|---|---|
| `SCFSteps` | Data recorded at each step of a self-consistent DFT calculation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.outputs.SCFSteps){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `energies_total` | m_float64(float) (shape: ['*']) | Total energy at each SCF step. |
| `delta_energies_total` | m_float64(float) (shape: ['*']) | Absolute change of total energy at each SCF step. |
| `delta_potential_rms` | m_float64(float) (shape: ['*']) | Root mean square of change of potential energy at each SCF step. |
| `delta_density_rms` | m_float64(float) (shape: ['*']) | Root mean square of change of potential energy at each SCF step. |
| `delta_wavefunction_rms` | m_float64(float) (shape: ['*']) | Root mean square of change of wavefunction coefficients at each SCF step. Dimensionless quantity representing convergence of orbital coefficients. |
| `delta_force_abs` | m_float64(float) (shape: ['*']) | Absolute change of forces at each SCF step. |
| `durations` | m_float64(float) (shape: ['*']) | Time spent at each SCF step. |
| `code_specific_quantities` | JSON | Code specific quantities that are recorded during SCF convergence. |

### `PhysicalProperty`

| Section | Description | MetaInfo |
|---|---|---|
| `PhysicalProperty` | A base section for computational output properties, containing all relevant (meta)data. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.physical_property.PhysicalProperty){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `name` | m_str(str) | Name of the physical property. Example: `'ElectronicBandGap'`. |
| `iri` | URL | Internationalized Resource Identifier (IRI) pointing to a definition, typically within a larger, ontological framework. |
| `type` | m_str(str) | Type categorization of the physical property. Example: an `ElectronicBandGap` can be `'direct'` or `'indirect'`. |
| `contribution_type` | m_str(str) | Type of contribution to the physical property. Hence, only applies to `contributions` instances. Example: `TotalEnergy` may have contributions like _kinetic_, _potential_, etc. |
| `label` | m_str(str) | Label for additional classification of the physical property. Example: an `ElectronicBandGap` can be labeled as `'DFT'` or `'GW'` depending on the methodology used to calculate it. |
| `entity_ref` | Reference | <details><summary>Reference to the entity that the physical property refers to.</summary>Reference to the entity that the physical property refers to. Examples:<br>- a simulated physical property might refer to the macroscopic system or instead of a specific atom in the unit<br>cell. In the first case, `outputs.model_system_ref` (see outputs.py) will point to the `ModelSystem` section,<br>while in the second case, `entity_ref` will point to `AtomsState` section (see atoms_state.py).</details> |
| `is_derived` | m_bool(bool) | <details><summary>Flag indicating whether the physical property is derived from other physical properties.</summary>Flag indicating whether the physical property is derived from other physical properties. We make<br>the distinction between directly parsed and derived physical properties:<br>- Directly parsed: the physical property is directly parsed from the simulation output files.<br>- Derived: the physical property is derived from other physical properties. No extra numerical settings<br>are required to calculate the physical property.</details> |
| `physical_property_ref` | Reference | Reference to the `PhysicalProperty` section from which the physical property was derived. If `physical_property_ref` is populated, the quantity `is_derived` is set to True via normalization. |
| `is_converged` | m_bool(bool) | Flag indicating whether the calculation that yields this physical property is converged or not after a SCF or optimization process. This information is obtained from the workflow section. |


