# `Outputs`

!!! warning
    This page is still under construction.

## Outputs

The `Outputs` section stores all simulation properties along with references to the corresponding `ModelMethod` and `ModelSystem` sections. Each property inherits from the abstract `PhysicalProperty` section, which defines the property `value` and may include a `variables` sub-section when the property depends on a varying parameter (e.g., Temperature).

For self-consistent calculations, the `SCFOutputs` section is used:

- **SCF Steps:** Contains repeated sub-sections (`scf_steps`) for each self-consistent iteration (e.g., storing Fermi level values like `[1, 1.5, 2, 2.1, 2.101]` eV).

- **Final Output:** Non-iterative properties are stored directly under `SCFOutputs` and include a reference to the `SelfConsistency` section.

- **Convergence Check:** The method `resolve_is_scf_converged()` determines whether a property (e.g., Fermi level) is converged. A very small `SelfConsistency.threshold_change` (e.g., `1e-24`) may result in a property being marked unconverged if the change between iterations is larger than this threshold.
 