# Symmetry

**Purpose:** Crystallographic symmetry: local/global symmetry, space groups, point groups, Bravais lattices

**In scope:**

- Local and global symmetry section hierarchy
- Space group symbols and numbers
- Point group symbols
- Bravais lattice classifications
- Symmetry operations


## Relationship map


<div class="uml-diagram-card" markdown="1">

```mermaid
classDiagram
    class GlobalCrystalSymmetry
    class GlobalSymmetry
    class LocalCrystalSymmetry
    class LocalSymmetry
    GlobalSymmetry <|-- GlobalCrystalSymmetry
    LocalSymmetry <|-- LocalCrystalSymmetry
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="54" y1="8" x2="22" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M10 8 L22 2 L22 14 Z"/></svg><span>inheritance (is-a)</span></div>
</div>

</div>


## Quantities by Key Sections

### `LocalSymmetry`

| Section | Description | MetaInfo |
|---|---|---|
| `LocalSymmetry` | Base class for per-particle local symmetry information. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.LocalSymmetry){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `equivalent_atoms` | m_int32(int32) (shape: ['*']) | <details><summary>Equivalence grouping of atoms by symmetry operations.</summary>Equivalence grouping of atoms by symmetry operations.<br>Atoms with the same index value are symmetrically equivalent.<br>Examples:<br>- [0, 1, 2, 3]: all four atoms are non-equivalent<br>- [0, 0, 0, 3]: first three atoms are equivalent, fourth is unique</details> |

### `LocalCrystalSymmetry`

| Section | Description | MetaInfo |
|---|---|---|
| `LocalCrystalSymmetry` | Crystallographic local symmetry for particles in a crystal structure. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.LocalCrystalSymmetry){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `site_symmetries` | m_str(str) (shape: ['*']) | <details><summary>Crystallographic point group symbol for each particle site in Hermann-Mauguin notation.</summary>Crystallographic point group symbol for each particle site in Hermann-Mauguin notation.<br>Each symbol (e.g., '3m', 'mmm', '432', '1') describes the local symmetry operations<br>that leave the atomic site invariant within the crystal structure. These are the<br>site symmetry groups—subgroups of the full space group that preserve the specific<br>atomic position.<br>The site symmetry is intrinsically linked to the Wyckoff position: atoms at the same<br>Wyckoff position share the same site symmetry, though the converse is not always true.<br>Higher symmetry positions (lower Wyckoff letters like 'a') typically have higher-order<br>site symmetries.<br>**Source**: Determined via spglib symmetry analysis (accessed through MatID), which<br>uses the geometric positions of atoms to identify symmetry operations.<br>Examples:<br>- '1' - No symmetry (general position)<br>- '3m' - Threefold rotation with mirror plane<br>- 'mmm' - Three perpendicular mirror planes (orthorhombic)<br>- '-43m' - Cubic tetrahedral symmetry</details> |
| `wyckoff_letters` | m_str(str) (shape: ['*']) | <details><summary>Wyckoff letter designation for each atomic position in this representation.</summary>Wyckoff letter designation for each atomic position in this representation.<br>Wyckoff positions are the crystallographically distinct positions in a space group, as defined in the<br>**International Tables for Crystallography** and accessible through resources like the **Bilbao<br>Crystallographic Server** (https://www.cryst.ehu.es/) and the **International Union of Crystallography<br>databases** (https://www.iucr.org/resources/data).<br>The Wyckoff letter (a, b, c, ...) identifies positions in order of **decreasing site symmetry**, with<br>`a` typically representing the **highest symmetry** (most special) position.<br>**Important**:<br>Wyckoff positions are determined using **geometric space group analysis** (via spglib/MatID),<br>which considers **only atomic positions** and ignores chemical species.<br>This means atoms of different elements may share the same Wyckoff designation<br>if they occupy geometrically equivalent positions.<br>For complete crystallographic uniqueness, combine `wyckoff_letters` with chemical information.<br>Use the `wyckoff_sites` property to get the combined letter+multiplicity format (e.g., "a1", "b2").<br>References:<br>- International Tables for Crystallography, Volume A: Space-group symmetry<br>- Aroyo, M.I. et al. (2006). "Bilbao Crystallographic Server." Z. Kristallogr. 221, 15-27<br>- Aroyo, M.I. et al. (2011). "Crystallography online: Bilbao Crystallographic Server."<br>Bulg. Chem. Commun. 43, 183-197</details> |
| `site_multiplicities` | m_int32(int32) (shape: ['*']) | <details><summary>Multiplicity of the Wyckoff site for each particle.</summary>Multiplicity of the Wyckoff site for each particle.<br>The **multiplicity** indicates how many symmetrically equivalent positions are generated by<br>applying all space group operations to this Wyckoff site within the **conventional unit cell**.<br>For example:<br>- Multiplicity 1: Special position with highest symmetry (unique in the unit cell)<br>- Multiplicity 2, 4, 8, etc.: Positions with lower symmetry that appear multiple times<br>Note: The multiplicity is determined from the conventional cell. In primitive cells or supercells,<br>fewer or more atoms of this type may be present, but the multiplicity value remains the same<br>as it's an intrinsic property of the Wyckoff position.</details> |

### `GlobalSymmetry`

| Section | Description | MetaInfo |
|---|---|---|
| `GlobalSymmetry` | A base section specifying the global symmetry of the corresponding `ModelSystem` at large, which can be used for categorization and lookup. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.GlobalSymmetry){:target="_blank"} |

*This section has no direct quantities.*

### `GlobalCrystalSymmetry`

| Section | Description | MetaInfo |
|---|---|---|
| `GlobalCrystalSymmetry` | A symmetry section specialized for identifying bulk crystal space groups. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.model_system.GlobalCrystalSymmetry){:target="_blank"} |

| Quantity | Type | Description |
|---|---|---|
| `lattice_type` | Enum | <details><summary>Bravais lattice type (crystal family classification).</summary>Bravais lattice type (crystal family classification).<br>The first lowercase letter of Pearson notation, identifying the crystal family<br>based on lattice symmetry:<br>**3D lattices:**<br>- a: triclinic<br>- m: monoclinic<br>- o: orthorhombic<br>- t: tetragonal<br>- r: trigonal<br>- h: hexagonal<br>- c: cubic<br>**2D lattices:**<br>- mp: oblique<br>- op: rectangular<br>- oc: centered rectangular<br>- tp: square<br>- hp: hexagonal 2D<br>**1D lattices:**<br>- ap: linear<br>This quantity enables independent querying of crystal families<br>(e.g., "all cubic systems" regardless of centering type).</details> |
| `lattice_centering` | Enum | <details><summary>Lattice centering type.</summary>Lattice centering type.<br>The second uppercase letter of Pearson notation, describing how lattice points<br>are distributed within the conventional unit cell:<br>**3D centerings:**<br>- P: primitive (lattice points only at cell corners)<br>- R: rhombohedral (hexagonal setting with 2/3, 1/3 centering)<br>- S: face centered (one pair of opposite faces centered)<br>- I: body centered (center of cell)<br>- F: all faces centered (all faces have centered points)<br>**2D centerings:**<br>- c: centered rectangular<br>- p: primitive 2D<br>**1D centerings:**<br>- p: primitive 1D<br>This quantity enables independent querying of centering types<br>(e.g., "all face-centered lattices" regardless of crystal family).</details> |
| `hall_symbol` | m_str(str) | <details><summary>Hall symbol for this system describing the minimum number of symmetry operations</summary>Hall symbol for this system describing the minimum number of symmetry operations<br>needed to uniquely define a space group. See https://cci.lbl.gov/sginfo/hall_symbols.html.<br>Examples:<br>- `F -4 2 3`,<br>- `-P 4 2`,<br>- `-F 4 2 3`.</details> |
| `hall_number` | m_int32(int32) | Hall number uniquely identifying the Hall symbol. This is an integer from 1 to 530 for 3D space groups, providing a numerical index into the Hall symbol table. Different settings or origin choices of the same space group have different Hall numbers. |
| `point_group_symbol` | m_str(str) | <details><summary>Symbol of the crystallographic point group in the Hermann-Mauguin notation.</summary>Symbol of the crystallographic point group in the Hermann-Mauguin notation. See<br>https://en.wikipedia.org/wiki/Crystallographic_point_group. Examples:<br>- `-43m`,<br>- `4/mmm`,<br>- `m-3m`.</details> |
| `space_group_number` | m_int32(int32) | <details><summary>Specifies the International Union of Crystallography (IUC) space group number of...</summary>Specifies the International Union of Crystallography (IUC) space group number of the 3D<br>space group of this system. See https://en.wikipedia.org/wiki/List_of_space_groups.<br>Examples:<br>- `216`,<br>- `123`,<br>- `225`.</details> |
| `space_group_symbol` | m_str(str) | <details><summary>Specifies the International Union of Crystallography (IUC) space group symbol of...</summary>Specifies the International Union of Crystallography (IUC) space group symbol of the 3D<br>space group of this system. See https://en.wikipedia.org/wiki/List_of_space_groups.<br>Examples:<br>- `F-43m`,<br>- `P4/mmm`,<br>- `Fm-3m`.</details> |
| `strukturbericht_designation` | m_str(str) | <details><summary>Classification of the material according to the historically grown and similar c...</summary>Classification of the material according to the historically grown and similar crystal<br>structures ('strukturbericht'). Useful when using altogether with `space_group_symbol`.<br>Examples:<br>- `C1B`, `B3`, `C15b`,<br>- `L10`, `L60`,<br>- `L21`.<br>Extracted from the AFLOW encyclopedia of crystallographic prototypes.</details> |
| `prototype_formula` | m_str(str) | <details><summary>The formula of the prototypical material for this structure as extracted from th...</summary>The formula of the prototypical material for this structure as extracted from the<br>AFLOW encyclopedia of crystallographic prototypes. It is a string with the chemical<br>symbols:<br>- https://aflowlib.org/prototype-encyclopedia/chemical_symbols.html</details> |
| `prototype_aflow_id` | m_str(str) | The identifier of this structure in the AFLOW encyclopedia of crystallographic prototypes: http://www.aflowlib.org/prototype-encyclopedia/index.html |
| `analysis_origin_shift` | m_float64(float64) (shape: [3]) | <details><summary>Origin shift vector (3-element) applied by spglib during symmetry standardization.</summary>Origin shift vector (3-element) applied by spglib during symmetry standardization.<br>This vector describes the shift from the standardized origin to the input structure's<br>origin in fractional coordinates. During symmetry analysis, spglib may shift the origin<br>to align with conventional crystallographic settings (e.g., placing inversion centers<br>or high-symmetry points at the origin).<br>The shift is applied as: **r_input = r_standardized + origin_shift**<br>where r_input is a position in the input structure and r_standardized is the<br>corresponding position in the standardized cell.<br>**Source**: Extracted from spglib's symmetry dataset via MatID's `SymmetryAnalyzer`.<br>**Note**: This transformation is specific to the symmetry analysis process and is<br>distinct from user-defined representation transformations.<br>See: https://spglib.readthedocs.io/en/stable/definition.html</details> |
| `analysis_transformation_matrix` | m_float64(float64) (shape: [3, 3]) | <details><summary>Transformation matrix (3×3) from input lattice vectors to standardized lattice vectors.</summary>Transformation matrix (3×3) from input lattice vectors to standardized lattice vectors.<br>This matrix describes how spglib transforms the input unit cell into a standardized<br>conventional cell during symmetry analysis. The transformation is defined such that:<br>**L_input = L_standardized @ transformation_matrix**<br>where L_input is the matrix of input lattice vectors (as columns) and L_standardized<br>is the matrix of standardized lattice vectors.<br>The standardization process orients the cell according to conventional crystallographic<br>settings for the identified space group, which may involve:<br>- Reorienting axes to align with symmetry elements<br>- Converting between primitive and conventional cells<br>- Standardizing the choice of basis vectors<br>**Source**: Extracted from spglib's symmetry dataset via MatID's `SymmetryAnalyzer`.<br>**Note**: This is specifically the transformation applied during symmetry detection<br>and is distinct from user-defined representation transformations.<br>See: https://spglib.readthedocs.io/en/stable/definition.html</details> |


## Related Pages

- [ModelSystem](../explanation/model_system/overview.md)
