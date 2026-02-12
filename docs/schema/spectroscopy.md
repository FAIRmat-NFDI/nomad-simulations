# Spectroscopic Properties

**Purpose:** Absorption spectra, XAS, and dielectric response

**In scope:**

- Spectral profile base class
- Absorption spectra from BSE calculations
- X-ray absorption spectra (XAS) from core hole calculations
- Frequency-dependent dielectric functions (permittivity)

**Out of scope:**

- Methods that compute spectra (BSE, CoreHoleSpectra in model_method)
- DOS profiles

## Relationship map


```mermaid
classDiagram
    class AbsorptionSpectrum
    class Energy2
    class Frequency
    class Permittivity
    class SpectralProfile
    class XASSpectrum
    SpectralProfile <|-- AbsorptionSpectrum
    AbsorptionSpectrum <|-- XASSpectrum
    Permittivity --> Frequency : frequencies
    SpectralProfile --> Energy2 : energies
    SpectralProfile --> Energy2 : frequencies
    XASSpectrum --> AbsorptionSpectrum : exafs_spectrum
    XASSpectrum --> AbsorptionSpectrum : xanes_spectrum
```

**Legend**

- `Parent <|-- Child`: inheritance (`Child` extends `Parent`)
- `Owner --> SubSection`: containment/subsection relationship
- `Source ..> Target`: typed reference from one section to another


## Key sections

| Section | Description | MetaInfo |
|---|---|---|
| `SpectralProfile` | A base section used to define the spectral profile. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.spectral_profile.SpectralProfile){:target="_blank"} |
| `AbsorptionSpectrum` |  | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.spectral_profile.AbsorptionSpectrum){:target="_blank"} |
| `XASSpectrum` | X-ray Absorption Spectrum (XAS). | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.spectral_profile.XASSpectrum){:target="_blank"} |
| `Permittivity` | Response of the material to polarize in the presence of an electric field. | [Open in MetaInfo browser](https://nomad-lab.eu/prod/v1/develop/gui/analyze/metainfo/nomad_simulations/section_definitions@nomad_simulations.schema_packages.properties.permittivity.Permittivity){:target="_blank"} |


## Quantities by section

### `SpectralProfile`

| Quantity | Type | Description |
|---|---|---|
| `value` | m_float_bounded(float) (shape: ['*']) | The value of the intensities of a spectral profile. Must be positive. |

### `AbsorptionSpectrum`

| Quantity | Type | Description |
|---|---|---|
| `axis` | Enum | Axis of the absorption spectrum. This is related with the polarization direction, and can be seen as the principal term in the tensor `Permittivity.value` (see permittivity.py module). |

### `XASSpectrum`

*This section has no direct quantities.*

### `Permittivity`

| Quantity | Type | Description |
|---|---|---|
| `type` | Enum | Type of permittivity which allows to identify if the permittivity depends on the frequency or not. |
| `value` | m_complex128(complex) (shape: ['*']) | Value of the permittivity tensor. If the value does not depend on the scattering vector `q`, then we can extract the optical absorption spectrum from the imaginary part of the permittivity tensor (this is also called macroscopic dielectric function). |

