# Simulation Entry

This page explains how the `Simulation` entry is modeled and used in practice.
For canonical quantity-level reference and class relationships, see [Schema Navigation: Simulation Entry](../schema/simulation.md).

## Scope and Ownership

The simulation entry combines three classes in `schema_packages/general.py`:

- `Program`: metadata about the software/code used for the calculation.
- `BaseSimulation`: shared simulation metadata (inherits from NOMAD base sections and includes `program`).
- `Simulation`: top-level entry section that links inputs and outputs of a simulation.

`Simulation` owns three repeating subsections:

- `model_system` (`ModelSystem` list)
- `model_method` (`ModelMethod` list)
- `outputs` (`Outputs` list)

It also stores `representative_system_index`, which points to the representative item in `model_system`.

## Normalization Behavior

During `Simulation.normalize()`:

1. Representative system consistency is enforced.
2. `representative_system_index` is set from `model_system` flags.
3. System hierarchy helper quantities are updated (`branch_depth`, `composition_formula`).

Important behavior from the current implementation:

- If no system is marked representative, the last system is promoted.
- If multiple systems are marked representative, only the last remains representative.
- If there is exactly one system and none was marked, index resolves to `0`.

These rules are implemented in `_validate_and_set_representative_system()` in `general.py`.

## Typical Parser Initialization

A practical parser pattern is to instantiate `Simulation`, set `Program`, then populate `model_system`/`model_method`/`outputs`.

```python
--8<-- "snippets/simulation_entry/program_setup.py"
```

## Workflows and Entry Granularity

A `Simulation` entry typically stores a single calculation context, including its SCF history where applicable.
More complex multi-step pipelines are represented via workflow schemas that connect one or more entries.

For workflow-specific modeling details, see:

- NOMAD simulation workflow plugin: <https://github.com/fairmat-nfdi/nomad-schema-plugin-simulation-workflow>
