# Spectroscopic Properties - Full Screen Diagram

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
    class AbsorptionSpectrum {
    }
    class DOSProfile {
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
    class PhysicalProperty {
    }
    class SpectralProfile {
    }
    class XASSpectrum {
    }
    SpectralProfile <|-- AbsorptionSpectrum
    SpectralProfile <|-- DOSProfile
    PhysicalProperty <|-- Permittivity
    PhysicalProperty <|-- SpectralProfile
    AbsorptionSpectrum <|-- XASSpectrum
    DOSProfile --> Energy2 : energies
    Outputs --> AbsorptionSpectrum : absorption_spectra
    Outputs --> Permittivity : permittivities
    Outputs --> XASSpectrum : xas_spectra
    Permittivity --> Frequency : frequencies
    Permittivity --> KMesh : q_mesh
    PhysicalProperty --> PhysicalProperty : contributions
    SpectralProfile --> Energy2 : energies
    SpectralProfile --> Energy2 : frequencies
    XASSpectrum --> AbsorptionSpectrum : exafs_spectrum
    XASSpectrum --> AbsorptionSpectrum : xanes_spectrum
```