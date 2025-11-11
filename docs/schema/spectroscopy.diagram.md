# Spectroscopy & Excitations - Full Screen Diagram

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
    class BSE {
    }
    class DFTGWModel {
    }
    class DFTGWResults {
    }
    class DFTGWWorkflow {
    }
    class ElectronicGreensFunction {
    }
    class ElectronicSelfEnergy {
    }
    class Outputs {
    }
    class QuasiparticleWeight {
    }
    class Screening {
    }
    class XASSpectrum {
    }
    Outputs --> AbsorptionSpectrum : absorption_spectra
    Outputs --> ElectronicGreensFunction
    Outputs --> ElectronicSelfEnergy : electronic_self_energies
    Outputs --> QuasiparticleWeight
    Outputs --> XASSpectrum : xas_spectra
    XASSpectrum --> AbsorptionSpectrum : exafs_spectrum
    XASSpectrum --> AbsorptionSpectrum : xanes_spectrum
```