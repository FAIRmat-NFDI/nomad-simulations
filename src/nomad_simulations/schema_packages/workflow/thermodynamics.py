import numpy as np
from nomad.datamodel import EntryArchive, SubSection
from nomad.metainfo import Quantity, SchemaPackage
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.workflow.trajectory import (
    TrajectoryProperty,
)
from nomad_simulations.schema_packages.utils import log

from .general import (
    SimulationWorkflow,
    SimulationWorkflowMethod,
    SimulationWorkflowOutputs,
)

from nomad_simulations.schema_packages.workflow.trajectory import SerialWorkflowOutputs

m_package = SchemaPackage()


class ThermodynamicsMethod(SimulationWorkflowMethod):
    _label = 'Thermodynamics method'


class ThermodynamicsOutputs(SerialWorkflowOutputs):
    _label = 'Thermodynamics ouputs'
    pass


class Thermodynamics(SimulationWorkflow):
    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = ThermodynamicsMethod()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = ThermodynamicsOutputs()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)


m_package.__init_metainfo__()
