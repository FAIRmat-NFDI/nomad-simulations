# Symmetry

**Purpose:** Crystallographic symmetry: space groups, point groups, Bravais lattices

**In scope:**

- Space group symbols and numbers
- Point group symbols
- Bravais lattice classifications
- Symmetry operations

**Out of scope:**

- Cell structure
- Atomic positions

## Relationship map


![symmetry_0 diagram](../assets/diagrams/symmetry_0.svg){: style="width: 40%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}

<div style="font-size: 0.9em; color: #666; margin-top: 8px; margin-bottom: 8px;">
<b>Legend:</b>
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="20" y1="6" x2="4" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="4,6 8,3 8,9" fill="none" stroke="currentColor" stroke-width="1.5"/></svg> inheritance ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> containment ·
<svg width="24" height="12" style="vertical-align: middle; margin: 0 2px;"><line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2,2"/><polygon points="20,6 16,3 16,9" fill="currentColor"/></svg> reference
</div>


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `Symmetry` | A base section used to specify the symmetry of the `AtomicCell`. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.Symmetry){:target="_blank"} |


## Quantities by section

### `Symmetry`

| Quantity | Type | Description |
|---|---|---|
| `bravais_lattice` | m_str(str) | <details><summary>Bravais lattice in Pearson notation.</summary>Bravais lattice in Pearson notation.<br>The first lowercase letter identifies the<br>crystal family: a (triclinic), b (monoclinic), o (orthorhombic), t (tetragonal),<br>h (hexagonal), c (cubic).<br>The second uppercase letter identifies the centring: P (primitive), S (face centered),<br>I (body centred), R (rhombohedral centring), F (all faces centred).</details> |
| `hall_symbol` | m_str(str) | <details><summary>Hall symbol for this system describing the minimum number of symmetry operations</summary>Hall symbol for this system describing the minimum number of symmetry operations<br>needed to uniquely define a space group. See https://cci.lbl.gov/sginfo/hall_symbols.html.<br>Examples:<br>- `F -4 2 3`,<br>- `-P 4 2`,<br>- `-F 4 2 3`.</details> |
| `point_group_symbol` | m_str(str) | <details><summary>Symbol of the crystallographic point group in the Hermann-Mauguin notation.</summary>Symbol of the crystallographic point group in the Hermann-Mauguin notation. See<br>https://en.wikipedia.org/wiki/Crystallographic_point_group. Examples:<br>- `-43m`,<br>- `4/mmm`,<br>- `m-3m`.</details> |
| `space_group_number` | m_int32(int32) | <details><summary>Specifies the International Union of Crystallography (IUC) space group number of...</summary>Specifies the International Union of Crystallography (IUC) space group number of the 3D<br>space group of this system. See https://en.wikipedia.org/wiki/List_of_space_groups.<br>Examples:<br>- `216`,<br>- `123`,<br>- `225`.</details> |
| `space_group_symbol` | m_str(str) | <details><summary>Specifies the International Union of Crystallography (IUC) space group symbol of...</summary>Specifies the International Union of Crystallography (IUC) space group symbol of the 3D<br>space group of this system. See https://en.wikipedia.org/wiki/List_of_space_groups.<br>Examples:<br>- `F-43m`,<br>- `P4/mmm`,<br>- `Fm-3m`.</details> |
| `strukturbericht_designation` | m_str(str) | <details><summary>Classification of the material according to the historically grown and similar c...</summary>Classification of the material according to the historically grown and similar crystal<br>structures ('strukturbericht'). Useful when using altogether with `space_group_symbol`.<br>Examples:<br>- `C1B`, `B3`, `C15b`,<br>- `L10`, `L60`,<br>- `L21`.<br>Extracted from the AFLOW encyclopedia of crystallographic prototypes.</details> |
| `prototype_formula` | m_str(str) | <details><summary>The formula of the prototypical material for this structure as extracted from th...</summary>The formula of the prototypical material for this structure as extracted from the<br>AFLOW encyclopedia of crystallographic prototypes. It is a string with the chemical<br>symbols:<br>- https://aflowlib.org/prototype-encyclopedia/chemical_symbols.html</details> |
| `prototype_aflow_id` | m_str(str) | The identifier of this structure in the AFLOW encyclopedia of crystallographic prototypes: http://www.aflowlib.org/prototype-encyclopedia/index.html |
| `atomic_cell_ref` | <nomad.metainfo.metainfo.Reference object at 0x76abc60441d0> | Reference to the AtomicCell section that the symmetry refers to. |

