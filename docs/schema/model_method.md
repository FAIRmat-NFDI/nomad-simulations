# Model Method

**Purpose:** Base method hierarchy: BaseModelMethod, ModelMethod, and ModelMethodElectronic


## Relationship map


<div class="uml-diagram-card" markdown="1">

```mermaid
classDiagram
    class BaseModelMethod
    class ModelMethod
    class ModelMethodElectronic
    BaseModelMethod <|-- ModelMethod
    ModelMethod <|-- ModelMethodElectronic
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="54" y1="8" x2="22" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M10 8 L22 2 L22 14 Z"/></svg><span>inheritance (is-a)</span></div>
</div>

</div>


## Quantities by Key Sections

### `BaseModelMethod`

| Section | Description | MetaInfo |
|---|---|---|
| `BaseModelMethod` | A base section used to define the abstract class of a Hamiltonian section. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.BaseModelMethod){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `name` | m_str(str) | Name of the mathematical model. This is typically used to identify the model Hamiltonian used in the simulation. Typical standard names: 'DFT', 'TB', 'GW', 'BSE', 'DMFT', 'NMR', 'kMC'. |
| `type` | m_str(str) | Identifier used to further specify the kind or sub-type of model Hamiltonian. Example: a TB model can be 'Wannier', 'DFTB', 'xTB' or 'Slater-Koster'. This quantity should be rewritten to a MEnum when inheriting from this class. |
| `external_reference` | URL | External reference to the model e.g. DOI, URL. |

### `ModelMethod`

| Section | Description | MetaInfo |
|---|---|---|
| `ModelMethod` | A base section for the method-defining choices of a simulation. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.ModelMethod){:target="_blank"} |

*This section has no direct quantities.*

### `ModelMethodElectronic`

| Section | Description | MetaInfo |
|---|---|---|
| `ModelMethodElectronic` | A base section used to define the parameters of a model Hamiltonian used in electronic structure calculations (TB, DFT, GW, BSE, DMFT, etc). | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_method.ModelMethodElectronic){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `is_spin_polarized` | m_bool(bool) | If the simulation is done considering the spin degrees of freedom (then there are two spin channels, 'down' and 'up') or not. |
| `determinant` | Enum | <details><summary>The spin-coupling form of the determinant used for the</summary>The spin-coupling form of the determinant used for the<br>self-consistent field (SCF) calculation.<br>- **restricted**  (RHF/RKS): α and β electrons share the same spatial orbitals<br>- **unrestricted** (UHF/UKS): α and β orbitals are optimized independently<br>- **restricted-open-shell** (ROHF/ROKS): closed-shell core with spin-unpaired electrons<br>sharing spatial orbitals in the open-shell manifold</details> |


## Related Pages

- [Model Method Overview](../explanation/model_method/overview.md)
- [ModelMethod vs NumericalSettings](../explanation/model_method/model_method_vs_numerical_settings.md)
