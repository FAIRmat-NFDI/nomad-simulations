# Atomic State Properties - Full Screen Diagram

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
    class AtomsState {
    }
    class CoreHole {
    }
    class HubbardInteractions {
    }
    class OrbitalsState {
    }
    AtomsState --> CoreHole
    AtomsState --> HubbardInteractions
    AtomsState --> OrbitalsState
```