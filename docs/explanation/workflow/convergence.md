# Convergence Targets: Schema Traversal Guide

This guide explains how convergence checking works in NOMAD simulations, focusing on how to navigate the archive structure to access convergence configuration and results.

Schema reference pages:

- [Workflow Core (Schema Navigation)](../../schema/workflow.md)
- [Workflow Convergence (Schema Navigation)](../../schema/workflow_convergence.md)
- [Geometry Optimization Workflow (Schema Navigation)](../../schema/workflow_geometry_optimization.md)

## Overview

Convergence targets define criteria for determining when iterative calculations (SCF cycles, geometry optimization steps) have reached acceptable solutions. The convergence system consists of:

- **Configuration** (in `workflow2.method.*`): Defines what to check and thresholds
- **Checking logic** (in target classes): Extracts values and compares to thresholds
- **Results** (in `workflow2.results.*`): Stores convergence status

## Quick Reference: Where to Find Convergence Data

| Archive Location | Type | Availability | Purpose |
|------------------|------|--------------|---------|
| `workflow2.method.convergence_targets` | `List[WorkflowConvergenceTarget]` | All workflows | Workflow-level convergence criteria |
| `workflow2.method.single_point_convergence_targets` | `List[WorkflowConvergenceTarget]` | GeometryOptimization only* | SCF convergence for subtasks (steps, frames, displacements) |
| `workflow2.results.is_converged` | `bool` | All workflows | Overall convergence status (all targets) |
| `workflow2.results.is_single_point_converged` | `bool` | GeometryOptimization only* | Aggregated SCF convergence (all subtasks) |
| `workflow2.results.convergence` | `List[WorkflowConvergenceResults]` | All workflows | Per-target convergence results |

**\* Current limitation**: `single_point_convergence_targets` and `is_single_point_converged` should be available to any workflow composed of SCF calculations (MolecularDynamics, Phonon, etc.), but are currently only implemented in GeometryOptimization. This is a schema design limitation, not a conceptual one.

Class hierarchies, quantity tables, and section-level metadata are maintained in the generated schema navigation pages linked above. This page focuses on traversal and interpretation patterns.

## Common Traversal Patterns

Convergence information can be accessed through several common patterns depending on what you need:

**Accessing Configuration**: To view what convergence criteria were defined for a workflow, access `archive.workflow2.method.convergence_targets` which returns a list of target objects. Each target has `threshold`, `threshold_type`, and other configuration fields. For workflows with SCF subtasks, `archive.workflow2.method.single_point_convergence_targets` (currently only in GeometryOptimization) defines SCF convergence criteria.

**Checking Overall Status**: The simplest check is `archive.workflow2.results.is_converged`, a boolean indicating whether all workflow-level convergence targets were reached. For workflows with SCF subtasks, `archive.workflow2.results.is_single_point_converged` (when available) indicates whether all SCF calculations converged.

**Per-Target Results**: To see which specific targets converged, iterate through `archive.workflow2.results.convergence`. Each element is a `WorkflowConvergenceResults` object with `convergence_target_ref` pointing back to the original target and `is_reached` showing the boolean status for that target.

**Nested Workflow Traversal**: For workflows with subtasks (like GeometryOptimization), each task in `archive.workflow2.tasks` can have its own `results.convergence` section. To aggregate across all subtasks, use JMESPath queries like `workflow2.tasks[*].results.convergence[*].is_reached` which returns a nested list of boolean values organized by subtask and target.

**Direct Data Access**: Convergence targets use annotation paths to locate data in the archive. For example, energy convergence reads from `archive.data.outputs[-1].scf_steps.delta_energies_total`. Understanding these paths (documented in each target class's `threshold` annotations) helps when debugging or manually inspecting convergence data.

## Nested Workflows with SCF Subtasks

Many workflows involve nested structures where each subtask contains SCF calculations with their own convergence criteria. This pattern applies to:

- **GeometryOptimization**: Each optimization step is an SCF calculation
- **MolecularDynamics**: Each MD frame can involve SCF (in ab initio MD)
- **Phonon**: Each atomic displacement requires SCF
- **ElasticConstants**: Each strained structure needs SCF

Currently only GeometryOptimization implements this pattern in the schema.

### Two-Level Convergence (GeometryOptimization Example)

```
GeometryOptimization
├── Workflow-level convergence (workflow2.method.convergence_targets)
│   └── Checks: forces, total energy differences between steps
└── SCF-level convergence (workflow2.method.single_point_convergence_targets)
    └── Checks: SCF convergence within each step
```

### Archive Structure

```
archive.workflow2 (GeometryOptimization)
├── method
│   ├── convergence_targets
│   │   └── [ForceConvergenceTarget]  # Geometry convergence
│   └── single_point_convergence_targets
│       └── [EnergyConvergenceTarget]  # SCF convergence
├── tasks[0] (SinglePoint for step 0)
│   └── results
│       └── convergence
│           └── [WorkflowConvergenceResults]  # SCF status for step 0
├── tasks[1] (SinglePoint for step 1)
│   └── results
│       └── convergence
│           └── [WorkflowConvergenceResults]  # SCF status for step 1
└── results
    ├── is_converged: bool  # Geometry convergence
    ├── is_single_point_converged: bool  # All SCF runs
    └── convergence
        └── [WorkflowConvergenceResults]  # Geometry target results
```

### Aggregating SCF Convergence

The `is_single_point_converged` field aggregates SCF convergence across all steps by collecting convergence results from all subtasks via JMESPath query `workflow2.tasks[*].results.convergence[*].is_reached`. This returns a nested list structure where each outer element represents a subtask (e.g., optimization step) and contains boolean convergence status for each target. The aggregation logic applies `all()` across both dimensions to determine if every target in every subtask converged.

## Convergence Annotation Paths

Targets use metainfo annotations to specify where to find data in the archive:

### Path Notation

- `@.property_name`: Relative to current output (`archive.data.outputs[-1]`)
- `workflow2.property_name`: Absolute from archive root
- `archive.property_name`: Explicit archive root path

