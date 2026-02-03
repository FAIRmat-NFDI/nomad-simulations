# Chemical Formula

**Purpose:** Chemical formulas in different formats: descriptive, reduced, IUPAC, Hill, anonymous

**In scope:**

- Descriptive formula
- Reduced formula
- IUPAC formula
- Hill formula
- Anonymous formula
- Automatic formula generation

**Out of scope:**

- Atomic positions
- Particle states

## Relationship map


![chemical_formula_0 diagram](../assets/diagrams/chemical_formula_0.svg){: style="width: 40%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}

<div style="font-size: 0.9em; color: #666; margin-top: 8px; margin-bottom: 8px;">
<b>Legend:</b>
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="20" y1="6" x2="4" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="4,6 8,3 8,9" fill="none" stroke="currentColor" stroke-width="1.5"/></svg> inheritance ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> containment ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2,2"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> reference
</div>


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `ChemicalFormula` | A base section used to store the chemical formulas of a `ModelSystem` in different formats. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.ChemicalFormula){:target="_blank"} |


## Quantities by section

### `ChemicalFormula`

| Quantity | Type | Description |
|---|---|---|
| `descriptive` | m_str(str) | The chemical formula of the system as a string to be descriptive of the computation. It is derived from `elemental_composition` if not specified, with non-reduced integer numbers for the proportions of the elements. |
| `reduced` | m_str(str) | Alphabetically sorted chemical formula with reduced integer chemical proportion numbers. The proportion number is omitted if it is 1. |
| `iupac` | m_str(str) | <details><summary>Chemical formula where the elements are ordered using a formal list based on</summary>Chemical formula where the elements are ordered using a formal list based on<br>electronegativity as defined in the IUPAC nomenclature of inorganic chemistry (2005):<br>- https://en.wikipedia.org/wiki/List_of_inorganic_compounds<br>Contains reduced integer chemical proportion numbers where the proportion number<br>is omitted if it is 1.</details> |
| `hill` | m_str(str) | Chemical formula where Carbon is placed first, then Hydrogen, and then all the other elements in alphabetical order. If Carbon is not present, the order is alphabetical. |
| `anonymous` | m_str(str) | <details><summary>Formula with the elements ordered by their reduced integer chemical proportion</summary>Formula with the elements ordered by their reduced integer chemical proportion<br>number, and the chemical species replaced by alphabetically ordered letters. The<br>proportion number is omitted if it is 1.<br>Examples: H2O becomes A2B and H2O2 becomes AB. The letters are drawn from the English<br>alphabet that may be extended by increasing the number of letters: A, B, ..., Z, Aa, Ab<br>and so on. This definition is in line with the similarly named OPTIMADE definition.</details> |

