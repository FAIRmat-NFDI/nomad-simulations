# Convergence Targets: Schema Traversal Guide

This guide explains how convergence checking works in NOMAD simulations, focusing on how to navigate the archive structure to access convergence configuration and results.

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

## Schema Structure

### Convergence Target Classes

Convergence targets are specialized classes that inherit from `WorkflowConvergenceTarget` base class. Each target type (Energy, Force, Potential, Charge, Wavefunction) is configured with a `threshold` value and `threshold_type` specifying how to compare computed values against that threshold. The `threshold` field uses `flexible_unit=True` to accept values with appropriate physical units for each target type. During normalization, targets use metainfo annotations to locate the relevant convergence data in the archive (e.g., SCF energy deltas, force magnitudes) and apply the appropriate comparison logic (`absolute`, `relative`, `maximum`, or `rms`) to determine if convergence has been reached.

### Workflow Method Classes

Convergence targets are configured in workflow method sections:

```python
# Base class (all workflows)
SimulationWorkflowMethod
    └── convergence_targets: List[WorkflowConvergenceTarget]

# Extended for workflows with SCF subtasks (currently only GeometryOptimization)
# Note: Should be available to MolecularDynamics, Phonon, etc. - design limitation
GeometryOptimizationModel (extends SimulationWorkflowMethod)
    ├── convergence_targets: List[WorkflowConvergenceTarget]  # Workflow-level
    └── single_point_convergence_targets: List[WorkflowConvergenceTarget]  # SCF-level
```

### Results Classes

Convergence results are stored in workflow results sections:

```python
# Base class (all workflows)
SimulationWorkflowResults
    ├── is_converged: bool
    └── convergence: List[WorkflowConvergenceResults]
        └── WorkflowConvergenceResults
            ├── convergence_target_ref: WorkflowConvergenceTarget
            └── is_reached: bool

# GeometryOptimization-specific
GeometryOptimizationResults (extends SimulationWorkflowResults)
    ├── is_converged: bool
    ├── is_single_point_converged: bool  # TODO: should be array
    └── convergence: List[WorkflowConvergenceResults]
```

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

The `is_single_point_converged` field aggregates SCF convergence across all steps:

```python
# In GeometryOptimization.normalize()
single_point_convergence_results = jmespath.search(
    'workflow2.tasks[*].results.convergence[*].is_reached',
    archive
)
# Returns: [[True, True], [True, True], [True, False], ...]
#          └─ step 0 ─┘  └─ step 1 ─┘  └─ step 2 ─┘

all_scf_converged = all(all(x) for x in single_point_convergence_results)
self.results.is_single_point_converged = all_scf_converged
```

**Note**: The `is_single_point_converged` field is currently a scalar boolean that aggregates across all steps. It should be an array with shape `['n_steps']` to preserve per-step information. See TODO comments in `geometry_optimization.py:90-96` and `geometry_optimization.py:274-276`.

## Convergence Annotation Paths

Targets use metainfo annotations to specify where to find data in the archive:

### Path Notation

- `@.property_name`: Relative to current output (`archive.data.outputs[-1]`)
- `workflow2.property_name`: Absolute from archive root
- `archive.property_name`: Explicit archive root path

### Examples by Target Type

```python
# EnergyConvergenceTarget
'@.scf_steps.delta_energies_total'
→ archive.data.outputs[-1].scf_steps.delta_energies_total

# ForceConvergenceTarget (with fallback)
['workflow2.results.final_force_maximum',
 '@.scf_steps.delta_force_abs']
→ Try workflow2.results.final_force_maximum first
→ Fall back to archive.data.outputs[-1].scf_steps.delta_force_abs

# PotentialConvergenceTarget
'@.scf_steps.delta_potential_rms'

# ChargeConvergenceTarget
'@.scf_steps.delta_density_rms'

# WavefunctionConvergenceTarget
'@.scf_steps.delta_wavefunction_rms'
```

## Complete Example: Single Point Calculation

```python
from nomad.datamodel import EntryArchive
from nomad.units import ureg
from nomad_simulations.schema_packages.workflow import SinglePoint, SinglePointMethod
from nomad_simulations.schema_packages.outputs import Outputs, SCFSteps
from nomad_simulations.schema_packages.workflow import EnergyConvergenceTarget

# Create archive
archive = EntryArchive()

# Populate raw data (as parser would do)
scf_steps = SCFSteps()
scf_steps.delta_energies_total = np.array([1e-6, 5e-7, 1e-8]) * ureg.joule
archive.data.outputs = [Outputs(scf_steps=scf_steps)]

# Create workflow with convergence target
workflow = SinglePoint()
workflow.method = SinglePointMethod()
workflow.method.convergence_targets = [
    EnergyConvergenceTarget(
        threshold=1e-6 * ureg.joule,
        threshold_type='absolute'
    )
]

# Normalize workflow (triggers convergence checking)
workflow.normalize(archive, logger)

# Access results
print(f"Overall converged: {workflow.results.is_converged}")  # True
print(f"Number of targets: {len(workflow.results.convergence)}")  # 1

for result in workflow.results.convergence:
    target = result.convergence_target_ref
    print(f"{target.m_def.name}: threshold={target.threshold}, reached={result.is_reached}")
    # EnergyConvergenceTarget: threshold=1e-06 joule, reached=True
```

## Related Files

- Schema definition: `src/nomad_simulations/schema_packages/workflow/general.py`
- Geometry optimization: `src/nomad_simulations/schema_packages/workflow/geometry_optimization.py`
- Comprehensive tests: `tests/workflow/test_convergence_targets.py`
- Parser example: `nomad-parser-plugins-simulation/src/nomad_simulation_parsers/parsers/exciting/parser.py`

## Known Limitations and TODOs

1. **`single_point_convergence_targets` should be in base class**: Currently only defined in `GeometryOptimizationModel`, but the concept applies to any workflow composed of SCF subtasks (MolecularDynamics, Phonon, ElasticConstants, etc.). Should be moved to `SimulationWorkflowMethod` base class.

2. **`is_single_point_converged` should be an array**: Currently aggregates across all subtasks into a single boolean, losing per-subtask granularity. Should be `shape=['n_steps']` or similar.

3. **Relative convergence incomplete**: The `'relative'` threshold type requires a reference value that is not consistently available. See `WorkflowConvergenceTarget._check_relative()` for implementation notes.

4. **Fallback path complexity**: `ForceConvergenceTarget` uses multiple fallback paths which can be difficult to debug when data is missing.
