# Workflows

**Purpose.** End-to-end procedures composed of tasks (e.g., SCF, MD, geometry optimization).**In scope:** task graphs, iteration loops, task references**Out of scope:** final results (handled in Results)
## Relationship map

```mermaid
classDiagram
    class GeometryOptimization
    class MolecularDynamics
    class ParallelWorkflow
    class SelfConsistency
    class SerialWorkflow
    class SimulationTask
    class SimulationWorkflow
    class SimulationWorkflowModel
    class SimulationWorkflowResults
    class SinglePoint
    class Task
    class Workflow
    SimulationWorkflow --> SimulationWorkflowModel : model
    SimulationWorkflow --> SimulationWorkflowResults : results
```


## Key sections- `Workflow` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `SimulationWorkflow` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `ParallelWorkflow` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `SerialWorkflow` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `GeometryOptimization` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `MolecularDynamics` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `SinglePoint` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `Task` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `SimulationTask` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)- `SelfConsistency` — [open in MetaInfo browser](https://nomad-lab.eu/prod/v1/gui/analyze/metainfo)
## Micro-examples

=== "YAML"
```yaml
Workflow:
  tasks:
  - {}
SimulationWorkflow:
  model: {}
  results: {}
ParallelWorkflow: {}
SerialWorkflow: {}
GeometryOptimization: {}
MolecularDynamics: {}
SinglePoint: {}
Task:
  name:
  - null
  section:
  - null
  inputs:
  - {}
  outputs:
  - {}
SimulationTask: {}
SelfConsistency:
  scf_minimization_algorithm:
  - null
  n_max_iterations:
  - null
  threshold_change:
  - null
  threshold_change_unit:
  - null
