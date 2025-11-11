# Vibrations, Phonons & Elastic - Full Screen Diagram

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
    class Elastic {
    }
    class ElasticModel {
    }
    class ElasticResults {
    }
    class Hessian {
    }
    class Phonon {
    }
    class PhononModel {
    }
    class PhononResults {
    }
    class StrainDiagrams {
    }
    ElasticResults --> StrainDiagrams
```