# Particle States - Full Screen Diagram

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
    class AtomicOrbitals {
    }
    class AtomsState {
    }
    class CGBeadState {
    }
    class CoreHole {
    }
    class ElectronicState {
    }
    class HubbardInteractions {
    }
    class ParticleState {
    }
    ParticleState <|-- AtomsState
    ParticleState <|-- CGBeadState
    AtomsState --> ElectronicState
    HubbardInteractions --> ElectronicState : orbitals_ref
```