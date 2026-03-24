# Stand-alone Usage

## Purpose

Understand how to instantiate schema classes and populate quantities directly in Python,
without parser-plugin complexity. The page ends with a short normalization-methods intro.

## Assignment 2.1: `Simulation` timing basics

!!! abstract "Assignment 2.1"
    Create a `Simulation` instance, assign `cpu1_start=0 s` and `cpu1_end=24 min 30 s`,
    and compute elapsed time in seconds and hours.

### Related schema diagrams

- [Schema Navigation > Simulation Entry](../schema/simulation.md)

??? success "Solution 2.1"
    ```python
    --8<-- "snippets/tutorials/part2_foundations/assignment_2_1.py"
    ```

## Assignment 2.2: `Program` typing and composition

!!! abstract "Assignment 2.2"
    Create a `Program(name='VASP', version='5.0.0')`, attach it to `Simulation.program`,
    then assign an integer to `version` and inspect the stored result.

### Related schema diagrams

- [Schema Navigation > Simulation Entry](../schema/simulation.md)

??? success "Solution 2.2"
    ```python
    --8<-- "snippets/tutorials/part2_foundations/assignment_2_2.py"
    ```

## Assignment 2.3: `DFT` under `Simulation.model_method`

!!! abstract "Assignment 2.3"
    Instantiate a `DFT` method and append it to `Simulation.model_method`.
    Use `DFT.xc` (`XCFunctional`) to represent XC identity in the current schema.

### Related schema diagrams

- [Schema Navigation > Model Method](../schema/model_method.md)
- [Schema Navigation > Model Method Electronic](../schema/model_method_electronic.md)

??? success "Solution 2.3"
    ```python
    --8<-- "snippets/tutorials/part2_foundations/assignment_2_3.py"
    ```

## Assignment 2.4: `SelfConsistency` in `numerical_settings`

!!! abstract "Assignment 2.4"
    Add `SelfConsistency(threshold_change=1e-3, threshold_change_unit='joule')`
    under `DFT.numerical_settings` and verify parent-child linkage.

### Related schema diagrams

- [Schema Navigation > Numerical Settings](../schema/numerical_settings.md)
- [Schema Navigation > Model Method](../schema/model_method.md)

??? success "Solution 2.4"
    ```python
    --8<-- "snippets/tutorials/part2_foundations/assignment_2_4.py"
    ```

## Assignment 2.5: `AtomsState` and atomic numbers

!!! abstract "Assignment 2.5"
    Create `AtomsState` entries for `Ga` and `As` and resolve atomic numbers.

### Related schema diagrams

- [Schema Navigation > Particle States](../schema/particle_states.md)

??? success "Solution 2.5"
    ```python
    --8<-- "snippets/tutorials/part2_foundations/assignment_2_5.py"
    ```

## Assignment 2.6: `ModelSystem`, `particle_states`, and chemical formulas

!!! abstract "Assignment 2.6"
    Build a representative `ModelSystem` with positions, lattice vectors,
    and `particle_states`, then normalize and inspect formula variants.

### Related schema diagrams

- [Schema Navigation > Model System](../schema/model_system.md)
- [Schema Navigation > Chemical Formula](../schema/chemical_formula.md)
- [Schema Navigation > Symmetry](../schema/symmetry.md)

??? success "Solution 2.6"
    ```python
    --8<-- "snippets/tutorials/part2_foundations/assignment_2_6.py"
    ```

!!! note "Current schema terminology"
    Legacy `AtomicCell/cell/atoms_state` patterns are replaced by direct `ModelSystem`
    geometry (`positions`, `lattice_vectors`, `periodic_boundary_conditions`) and
    per-particle data in `particle_states`.

## Assignment 2.7: `Outputs`, references, and SCF deltas

!!! abstract "Assignment 2.7"
    Create an `Outputs` section with `SCFSteps` and `TotalEnergy` values across steps,
    normalize, and verify automatic `model_system_ref`, `model_method_ref`, and
    `delta_energies_total` population.

### Related schema diagrams

- [Schema Navigation > Outputs](../schema/outputs.md)
- [Schema Navigation > Model System](../schema/model_system.md)
- [Schema Navigation > Model Method](../schema/model_method.md)

??? success "Solution 2.7"
    ```python
    --8<-- "snippets/tutorials/part2_foundations/assignment_2_7.py"
    ```

## Assignment 2.8: output-property collections and spin channels

!!! abstract "Assignment 2.8"
    Store scalar and spin-resolved `ElectronicBandGap` entries in `Outputs` and
    extract spin-polarized entries with `extract_spin_polarized_property`.

### Related schema diagrams

- [Schema Navigation > Outputs](../schema/outputs.md)
- [Schema Navigation > Electronic Structure Properties](../schema/electronic_properties.md)

??? success "Solution 2.8"
    ```python
    --8<-- "snippets/tutorials/part2_foundations/assignment_2_8.py"
    ```

!!! note "About variable-dependent properties"
    The old generic `variables` pattern previously shown for `ElectronicBandGap` is not
    the current design. Variable grids are now represented by property-specific sections
    (for example DOS/ spectra energy grids).

## Normalization Exercises

The following exercises focus on practical normalization behavior from current tests.

### Exercise N1: representative `ModelSystem` normalization

!!! abstract "Exercise N1"
    Normalize a representative atomic `ModelSystem` and confirm that derived
    fields (`type`, `chemical_formula`) are populated.

??? success "Solution N1"
    ```python
    --8<-- "snippets/tutorials/part2_foundations/normalization_exercise_1.py"
    ```

### Exercise N2: `Outputs` SCF deltas from total energies

!!! abstract "Exercise N2"
    Populate only `total_energies` and run `Outputs.normalize(...)` to confirm
    that `scf_steps.delta_energies_total` is computed automatically.

??? success "Solution N2"
    ```python
    --8<-- "snippets/tutorials/part2_foundations/normalization_exercise_2.py"
    ```

For full normalization execution-order rules, see [Normalization](../explanation/normalize.md).

## Related Pages

- [Simulation Entry](../explanation/simulation_entry.md)
- [Model Method Overview](../explanation/model_method/overview.md)
- [ModelMethod vs NumericalSettings](../explanation/model_method/model_method_vs_numerical_settings.md)
- [Model System](../explanation/model_system/model_system.md)
- [Model System Usage Guidelines](../explanation/model_system/usage_guidelines.md)
