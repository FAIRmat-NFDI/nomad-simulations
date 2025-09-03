from typing import TYPE_CHECKING, Optional

from nomad.metainfo import MEnum, Quantity, SubSection
from nomad.metainfo.data_type import m_complex128

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties.spectral_profile import (
    AbsorptionSpectrum,
)
from nomad_simulations.schema_packages.variables import Frequency, KMesh

# TODO add `DielectricStrength` when we have examples and understand how to extract it from the `Permittivity` tensor.


class Permittivity(PhysicalProperty):
    """
    Response of the material to polarize in the presence of an electric field.

    Alternative names: `DielectricFunction`.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/Permittivity'

    # Class-level constants
    rank = [3, 3]
    _axes_map = ['xx', 'yy', 'zz']

    type = Quantity(
        type=MEnum('static', 'dynamic'),
        description="""
        Type of permittivity which allows to identify if the permittivity depends on the frequency or not.
        """,
    )

    value = Quantity(
        type=m_complex128().no_shape_check(),
        # unit='joule',  # TODO check units (they have to match `SpectralProfile.value`)
        shape=['*'],
        description="""
        Value of the permittivity tensor. If the value does not depend on the scattering vector `q`, then we
        can extract the optical absorption spectrum from the imaginary part of the permittivity tensor (this is also called
        macroscopic dielectric function).
        """,
    )

    frequencies = SubSection(sub_section=Frequency.m_def)

    q_mesh = SubSection(sub_section=KMesh.m_def)

    # ? We need use cases to understand if we need to define contributions to the permittivity tensor.
    # ? `ionic` and `electronic` contributions are common in the literature.

    def resolve_type(self) -> str:
        return 'static' if self.frequencies is None else 'dynamic'

    def extract_absorption_spectra(
        self, logger: 'BoundLogger'
    ) -> list[AbsorptionSpectrum] | None:
        """
        Extract the absorption spectrum from the imaginary part of the permittivity tensor.
        """
        if self.q_mesh is not None:
            logger.warning(
                'The `permittivity` depends on the scattering vector `q`, so that we cannot extract the absorption spectrum.'
            )
            return None
        if self.frequencies is None:
            logger.warning(
                'The `permittivity` does not have a `Frequency` variable to extract the absorption spectrum.'
            )
            return None
        # Define the `absorption_spectra` for each principal direction along the diagonal of the `Permittivity.value` as the imaginary part
        spectra = []
        for i in range(3):
            val = self.value[:, i, i].imag
            absorption_spectrum = AbsorptionSpectrum(
                axis=self._axes_map[i],
                frequencies=self.frequencies,
                value=val,
                physical_property_ref=self,  # ?
            )
            spectra.append(absorption_spectrum)
        return spectra

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Resolve the `type` of permittivity
        self.type = self.resolve_type()

        # `AbsorptionSpectrum` extraction
        absorption_spectra = self.extract_absorption_spectra(logger)
        if absorption_spectra is not None:
            self.m_parent.absorption_spectrum = absorption_spectra
