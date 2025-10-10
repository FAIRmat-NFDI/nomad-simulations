import numpy as np
from nomad.datamodel import EntryArchive, SubSection
from nomad.metainfo import Quantity, SchemaPackage
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.workflow.trajectory import (
    ConfigurationalProperty,
)
from nomad_simulations.schema_packages.utils import log

from .general import (
    SimulationWorkflow,
    SimulationWorkflowMethod,
    SimulationWorkflowResults,
    SerialWorkflowResults,
)

m_package = SchemaPackage()


class ThermodynamicsMethod(SimulationWorkflowMethod):
    _label = 'Thermodynamics method'


class ThermodynamicsResults(SerialWorkflowResults):
    _label = 'Thermodynamics ouputs'
    pass


class Thermodynamics(SimulationWorkflow):
    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.method:
            self.method = ThermodynamicsMethod()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = ThermodynamicsResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)


m_package.__init_metainfo__()
