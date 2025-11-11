# System & Geometry - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes in this vertical:

- **Solid arrows** (-->) represent SubSection containment
- **Dashed arrows** (..->) represent Quantity references

```mermaid
classDiagram
    class AtomicCell {
    }
    class BaseGreensFunction {
    }
    class Cell {
    }
    class ChemicalFormula {
    }
    class KLinePath {
    }
    class KMesh {
    }
    class KSpace {
    }
    class ModelSystem {
    }
    class ParticleState {
    }
    class Permittivity {
    }
    class Simulation {
    }
    class Symmetry {
    }
    class System {
    }
    BaseGreensFunction --> KMesh
    KSpace --> KLinePath
    KSpace --> KMesh
    ModelSystem --> Cell
    ModelSystem --> ChemicalFormula
    ModelSystem --> ModelSystem : sub_systems
    ModelSystem --> ParticleState
    ModelSystem --> Symmetry
    Permittivity --> KMesh : q_mesh
    Simulation --> ModelSystem
```