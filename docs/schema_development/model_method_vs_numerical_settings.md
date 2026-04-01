# ModelMethod vs NumericalSettings

## Purpose

This page explains how to decide whether information belongs in
`ModelMethod` or `NumericalSettings`.

For generated structure and quantity tables, use:

- [Model Method (Schema Navigation)](../schema/model_method.md)
- [Numerical Settings (Schema Navigation)](../schema/numerical_settings.md)

## Core Distinction

- `ModelMethod` answers: what mathematical model or physical approximation is
  being solved?
- `NumericalSettings` answers: how is that chosen model realized,
  discretized, converged, or evaluated in practice?

In schema terms, the split is primarily semantic, but it also has technical
value. `NumericalSettings` are attached to a specific method instance through
`BaseModelMethod.numerical_settings`, so they remain method-scoped without
being mixed into the method taxonomy itself.

## Decision Heuristics

Put information in `ModelMethod` when changing it would change at least one of
the following:

- the target Hamiltonian or operator content,
- the governing equations or ansatz,
- the physical approximation being made,
- the method family or subtype used to interpret the result.

Put information in `NumericalSettings` when changing it mainly affects:

- discretization or sampling,
- convergence behavior,
- basis or auxiliary representation choices,
- solver execution details,
- code-specific evaluation knobs for a fixed method.

A practical test is:

1. If two calculations would still be described as "the same method, but with
   different convergence/setup choices", use `NumericalSettings`.
2. If changing the value means you would cite a different approximation,
   Hamiltonian term, or method flavor in the methods section of a paper, use
   `ModelMethod`.

## Common Cases

Use `ModelMethod` for:

- `DFT`, `TB`, `GW`, `BSE`, `DMFT`, `HF`,
- XC functional identity,
- relativistic treatment as a physical approximation,
- active-space or multireference method definition,
- implicit-solvent or dispersion model family selection.

Use `NumericalSettings` for:

- k-point meshes and k-line paths,
- SCF thresholds and iteration limits,
- smearing controls,
- basis-set containers and basis tiers,
- pseudopotential metadata used to realize the calculation,
- surface tessellation, PB/GB grids, and other solver-side solvation knobs,
- dispersion switches or typed numerical knobs.

## Edge Cases

Some concepts naturally split across both sections.

`ImplicitSolvationModel` versus `SolvationSettings`:
The model family itself belongs in `ModelMethod`; tessellation, dielectric-grid,
or solver controls belong in `NumericalSettings`.

`EmpiricalDispersionModel` versus `EmpiricalDispersionSettings`:
The correction family belongs in `ModelMethod`; term switches, partitioning
choices, and scalar tuning knobs belong in `NumericalSettings`.

Basis sets and pseudopotentials:
These strongly affect numerical quality and sometimes practical transferability,
but in this schema they are treated as the numerical realization attached to a
chosen method, not as the method identity itself.

## Why Keep the Split

Keeping the split as separate sections is useful because it:

- preserves a stable method identity across convergence studies and code-level
  setup changes,
- keeps method taxonomy distinct from code-specific numerical controls,
- makes method descriptions easier to compare across codes,
- avoids overloading one section with both physical meaning and execution
  details.

The intended rule is therefore not "everything important goes into
`ModelMethod`". The rule is "keep model semantics in `ModelMethod`, and keep
their numerical realization in `NumericalSettings`".

## Pitfalls

- Do not duplicate the same concept in both sections just because a code places
  the keywords close together in its input file.
- Do not treat every code-specific input keyword as `ModelMethod`; many belong
  only to numerical controls.
- When a concept has both a model identity and a realization layer, model them
  separately rather than forcing one mixed section.

## Related Pages

- [Model Method Overview](../explanation/model_method/overview.md)
- [Basis Sets](../explanation/model_method/basis_sets.md)
- [Simulation Entry](../explanation/simulation_entry.md)