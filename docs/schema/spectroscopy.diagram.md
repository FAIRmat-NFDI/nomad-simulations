# Spectroscopic Properties - Full Screen Diagram

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
    class AbsorptionSpectrum {
    }
    class Energy2 {
    }
    class Frequency {
    }
    class KMesh {
    }
    class Outputs {
    }
    class Permittivity {
    }
    class SpectralProfile {
    }
    class XASSpectrum {
    }
    Outputs --> AbsorptionSpectrum : absorption_spectra
    Outputs --> Permittivity : permittivities
    Outputs --> XASSpectrum : xas_spectra
    Permittivity --> Frequency : frequencies
    Permittivity --> KMesh : q_mesh
    SpectralProfile --> Energy2 : energies
    SpectralProfile --> Energy2 : frequencies
    XASSpectrum --> AbsorptionSpectrum : exafs_spectrum
    XASSpectrum --> AbsorptionSpectrum : xanes_spectrum
```