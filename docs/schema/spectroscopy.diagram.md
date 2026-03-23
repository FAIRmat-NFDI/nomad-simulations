# Spectroscopic Properties - Full Screen Diagram

!!! tip "Interactive Zoom & Pan"
    - **Scroll wheel** or **+/-** buttons to zoom
    - **Click and drag** to pan
    - **Keyboard shortcuts**: `+`/`-` to zoom, `0` to reset, `f` to fit
    - **↗** button to open in separate window
    - **⬇** button to download as SVG

This diagram shows the relationships between schema classes:

<div class="uml-diagram-card" markdown="1">

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
    Permittivity *-- Frequency : frequencies
    SpectralProfile *-- Energy2 : energies
    SpectralProfile *-- Energy2 : frequencies
    XASSpectrum *-- AbsorptionSpectrum : exafs_spectrum
    XASSpectrum *-- AbsorptionSpectrum : xanes_spectrum
```

<p class="uml-legend__title">Legend</p>
<div class="uml-legend" role="list" aria-label="Diagram relationship legend">
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><line class="uml-legend__line" x1="54" y1="8" x2="28" y2="8"/><path class="uml-legend__head uml-legend__head--open" d="M18 8 L30 2 L30 14 Z"/></svg><span>inheritance (is-a)</span></div>
<div class="uml-legend__item" role="listitem"><svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true"><path class="uml-legend__head uml-legend__head--filled" d="M10 8 L16 2 L22 8 L16 14 Z"/><line class="uml-legend__line" x1="22" y1="8" x2="52" y2="8"/></svg><span>composition (has-a)</span></div>
</div>

</div>
