# Model System - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes:

- `Owner --> SubSection`: containment/subsection relationship
- `Source ..> Target`: typed reference from one section to another
- `Parent <|-- Child`: inheritance (`Child` extends `Parent`)

```mermaid
classDiagram
    class AlternativeRepresentation {
    }
    class ChemicalFormula {
    }
    class ElectronicState {
    }
    class GlobalSymmetry {
    }
    class ModelSystem {
    }
    class ParticleState {
    }
    class Representation {
    }
    Representation <|-- AlternativeRepresentation
    Representation <|-- ModelSystem
    ModelSystem --> AlternativeRepresentation : representations
    ModelSystem --> ChemicalFormula
    ModelSystem --> ElectronicState
    ModelSystem --> GlobalSymmetry : symmetry
    ModelSystem --> ParticleState
```