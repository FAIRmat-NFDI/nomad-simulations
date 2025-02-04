import numpy as np
from nomad.datamodel import EntryArchive
from nomad.metainfo import Quantity, SchemaPackage
from structlog.stdlib import BoundLogger

from .general import (
    SimulationWorkflow,
    SimulationWorkflowModel,
    SimulationWorkflowResults,
)

m_package = SchemaPackage()


class ThermodynamicsModel(SimulationWorkflowModel):
    label = 'Thermodynamics model'


class ThermodynamicsResults(SimulationWorkflowResults):
    label = 'Thermodynamics results'

    n_values = Quantity(
        type=int,
        shape=[],
        description="""
        Number of thermodynamics property evaluations.
        """,
    )

    temperature = Quantity(
        type=np.float64,
        shape=['n_values'],
        unit='kelvin',
        description="""
        Specifies the temperatures at which properties such as the Helmholtz free energy
        are calculated.
        """,
    )

    pressure = Quantity(
        type=np.float64,
        shape=['n_values'],
        unit='pascal',
        description="""
        Array containing the values of the pressure (one third of the trace of the stress
        tensor) corresponding to each property evaluation.
        """,
    )


class Thermodynamics(SimulationWorkflow):
    def map_inputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.model:
            self.model = ThermodynamicsModel()
        super().map_inputs(archive, logger)

    def map_outputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.results:
            self.results = ThermodynamicsResults()
        super().map_outputs(archive, logger)


m_package.__init_metainfo__()
