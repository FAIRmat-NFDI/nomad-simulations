import numpy as np
from nomad.datamodel import EntryArchive
from nomad.metainfo import Quantity, Reference, SchemaPackage

from nomad_simulations.schema_packages.model_method import BSE as BSEMethodology
from nomad_simulations.schema_packages.properties import SpectralProfile as Spectra
from nomad_simulations.schema_packages.utils import log

from .general import (
    ParallelWorkflow,
    SimulationWorkflowModel,
    SimulationWorkflowResults,
)

m_package = SchemaPackage()


class PhotonPolarizationModel(SimulationWorkflowModel):
    """Defines the full macroscopic dielectric tensor methodology: BSE method reference."""

    # TODO add TDDFT methodology reference.

    _label = 'Photon polarization workflow parameters'

    bse_method_ref = Quantity(
        type=Reference(BSEMethodology),
        description="""
        BSE methodology reference.
        """,
    )


class PhotonPolarizationResults(SimulationWorkflowResults):
    """Groups all polarization outputs: spectrum."""

    _label = 'Photon polarization workflow results'

    n_polarizations = Quantity(
        type=np.int32,
        description="""
        Number of polarizations for the phonons used for the calculations.
        """,
    )

    spectrum_polarization = Quantity(
        type=Reference(Spectra),
        shape=['n_polarizations'],
        description="""
        Spectrum for a given polarization of the photon.
        """,
    )


class PhotonPolarizationWorkflow(ParallelWorkflow):
    """
    Definitions for photon polarization workflow.
    """

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = PhotonPolarizationModel()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = PhotonPolarizationResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)


m_package.__init_metainfo__()
