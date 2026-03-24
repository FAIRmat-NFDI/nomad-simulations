# Workflow Convergence Design Notes

This file captures contributor-focused implementation context and open technical
work for convergence handling in workflow schemas. It is intentionally kept
outside published docs.

## Related Files

- `src/nomad_simulations/schema_packages/workflow/general.py`
- `src/nomad_simulations/schema_packages/workflow/geometry_optimization.py`
- `tests/workflow/test_convergence_targets.py`
- `nomad-parser-plugins-simulation/src/nomad_simulation_parsers/parsers/exciting/parser.py`

## Known Limitations and TODOs

1. `single_point_convergence_targets` should be in base class:
   currently only defined in `GeometryOptimizationModel`, but conceptually
   applies to any workflow composed of SCF subtasks (MolecularDynamics,
   Phonon, ElasticConstants, etc.). Target class for relocation:
   `SimulationWorkflowMethod`.

2. `is_single_point_converged` should be an array:
   currently aggregates all subtasks into one boolean, losing per-subtask
   granularity. Candidate shape: `['n_steps']` (or analogous task axis).

3. Relative convergence is incomplete:
   `threshold_type='relative'` requires a robust reference value strategy that
   is not consistently available across workflows.

4. Fallback path complexity:
   `ForceConvergenceTarget` uses multiple fallback paths; failure debugging is
   currently non-trivial when expected data is absent.

## Rationale for Public/Private Split

The public guide in `docs/explanation/workflow/convergence.md` focuses on
archive traversal and interpretation. Class inventories, quantity tables, and
schema hierarchy are already generated in `docs/schema/workflow*.md`, so they
should not be duplicated in the explanation layer.
