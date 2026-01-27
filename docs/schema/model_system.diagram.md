# Model System - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes:

- **Solid arrows** (-->) represent SubSection containment
- **Dashed arrows** (..->) represent Quantity references
- **Inheritance arrows** (<|--) represent class inheritance

```mermaid
classDiagram
    class AtomicCell {
    }
    class AtomsState {
    }
    class CGBeadState {
    }
    class Cell {
    }
    class ChemicalFormula {
    }
    class CoreHole {
    }
    class GeometricSpace {
    }
    class HubbardInteractions {
    }
    class ModelSystem {
    }
    class OrbitalsState {
    }
    class ParticleState {
    }
    class Simulation {
    }
    class Symmetry {
    }
    Cell <|-- AtomicCell
    ParticleState <|-- AtomsState
    ParticleState <|-- CGBeadState
    GeometricSpace <|-- Cell
    AtomsState --> CoreHole
    AtomsState --> HubbardInteractions
    AtomsState --> OrbitalsState
    ModelSystem --> Cell
    ModelSystem --> ChemicalFormula
    ModelSystem --> ModelSystem : sub_systems
    ModelSystem --> ParticleState
    ModelSystem --> Symmetry
    Simulation --> ModelSystem
```