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


![symmetry_0 diagram](../assets/diagrams/symmetry_0.svg){: style="width: 80%; cursor: pointer;" class="click-zoom-img" title="Click to zoom"}

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


## Micro-examples

=== "YAML"

    ```yaml
    Symmetry:
      bravais_lattice:
      - null
      hall_symbol:
      - null
      point_group_symbol:
      - null
      space_group_number:
      - null
      space_group_symbol:
      - null
      strukturbericht_designation:
      - null
      prototype_formula:
      - null
      prototype_aflow_id:
      - null
      atomic_cell_ref:
      - null
    ```