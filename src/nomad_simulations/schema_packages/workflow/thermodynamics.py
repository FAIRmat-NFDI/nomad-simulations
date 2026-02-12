import numpy as np
from nomad.datamodel import EntryArchive, SubSection
from nomad.metainfo import Quantity, SchemaPackage
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log
from nomad_simulations.schema_packages.workflow.trajectory import (
    ConfigurationalProperty,
)

from .general import (
    SerialWorkflowResults,
    SimulationWorkflow,
    SimulationWorkflowMethod,
    SimulationWorkflowResults,
)

m_package = SchemaPackage()


# TODO Can this class be removed and thermodynamic quantities simply added to SerialWorkflowResults?
class ThermodynamicsMethod(SimulationWorkflowMethod):
    _label = 'Thermodynamics method'


class ThermodynamicsResults(SerialWorkflowResults):
    _label = 'Thermodynamics results'
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
