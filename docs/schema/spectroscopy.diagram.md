# Spectroscopic Properties - Full Screen Diagram

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
    class AbsorptionSpectrum {
    }
    class Energy2 {
    }
    class Frequency {
    }
    class Permittivity {
    }
    class SpectralProfile {
    }
    class XASSpectrum {
    }
    SpectralProfile <|-- AbsorptionSpectrum
    AbsorptionSpectrum <|-- XASSpectrum
    Permittivity --> Frequency : frequencies
    SpectralProfile --> Energy2 : energies
    SpectralProfile --> Energy2 : frequencies
    XASSpectrum --> AbsorptionSpectrum : exafs_spectrum
    XASSpectrum --> AbsorptionSpectrum : xanes_spectrum
```