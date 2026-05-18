# Molecular Dynamics Workflow - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes:

<div class="uml-diagram-card" markdown="1">

```mermaid
classDiagram
    class BarostatParameters
    class CorrelationFunction
    class DiffusionConstant
    class EnsembleProperty
    class FreeEnergyCalculationParameters
    class Lambdas
    class MDSettings
    class MeanSquaredDisplacement
    class MolecularDynamics
    class MolecularDynamicsMethod
    class MolecularDynamicsResults
    class NumericalSettings
    class PhysicalProperty
    class RadialDistributionFunction
    class SerialWorkflow
    class SerialWorkflowResults
    class ShearParameters
    class SimulationWorkflowMethod
    class ThermostatParameters
    MDSettings <|-- BarostatParameters
    PhysicalProperty <|-- CorrelationFunction
    EnsembleProperty <|-- DiffusionConstant
    PhysicalProperty <|-- EnsembleProperty
    MDSettings <|-- FreeEnergyCalculationParameters
    NumericalSettings <|-- MDSettings
    CorrelationFunction <|-- MeanSquaredDisplacement
    SerialWorkflow <|-- MolecularDynamics
    SimulationWorkflowMethod <|-- MolecularDynamicsMethod
    SerialWorkflowResults <|-- MolecularDynamicsResults
    EnsembleProperty <|-- RadialDistributionFunction
    MDSettings <|-- ShearParameters
    MDSettings <|-- ThermostatParameters
    FreeEnergyCalculationParameters *-- Lambdas
    MolecularDynamics *-- MolecularDynamicsMethod : method
    MolecularDynamics *-- MolecularDynamicsResults : results
    MolecularDynamicsMethod *-- BarostatParameters
    MolecularDynamicsMethod *-- FreeEnergyCalculationParameters
    MolecularDynamicsMethod *-- ShearParameters
    MolecularDynamicsMethod *-- ThermostatParameters
    MolecularDynamicsResults *-- DiffusionConstant
    MolecularDynamicsResults *-- MeanSquaredDisplacement
    MolecularDynamicsResults *-- RadialDistributionFunction
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="54" y1="8" x2="22" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M10 8 L22 2 L22 14 Z"/></svg><span>inheritance (is-a)</span></div>
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><path class="uml-legend__head uml-legend__head--filled" d="M10 8 L16 2 L22 8 L16 14 Z"/><line class="uml-legend__line" x1="22" y1="8" x2="52" y2="8"/></svg><span>composition (has-a)</span></div>
</div>

</div>
