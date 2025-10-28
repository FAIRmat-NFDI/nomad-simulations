import numpy as np
from ase.eos import EquationOfState as aseEOS
from nomad.atomutils import get_volume
from nomad.datamodel import EntryArchive
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import (
    MEnum,
    Quantity,
    Reference,
    SchemaPackage,
    Section,
    SubSection,
)
from nomad.units import ureg
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.general import Program
from nomad_simulations.schema_packages.utils import log

from .general import (
    ParallelWorkflow,
    SimulationWorkflowModel,
    SimulationWorkflowResults,
)

m_package = SchemaPackage()


FUNCTION_NAMES = {
    'birch_murnaghan': 'birchmurnaghan',
    'pourier_tarantola': 'pouriertarantola',
    'vinet': 'vinet',
    'murnaghan': 'murnaghan',
    'birch_euler': 'birch',
}


class EquationOfStateModel(SimulationWorkflowModel):
    _label = 'EquationOfState workflow parameters'

    program = Quantity(
        type=Reference(Program),
        shape=[],
        description="""
        Program used to calculate the energies.
        """,
    )

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if self.program is None:
            try:
                self.program = archive.data.program
            except Exception:
                logger.error('Program not found.')


class EOSFit(ArchiveSection):
    """
    Section containing results of an equation of state fit.
    """

    m_def = Section(validate=False)

    function_name = Quantity(
        type=MEnum(*tuple(FUNCTION_NAMES.keys())),
        shape=[],
        description="""
        Specifies the function used to perform the fitting of the volume-energy data. Value
        can be one of birch_euler, birch_lagrange, birch_murnaghan, mie_gruneisen,
        murnaghan, pack_evans_james, poirier_tarantola, tait, vinet.
        """,
    )

    fitted_energies = Quantity(
        type=np.float64,
        shape=['*'],
        unit='joule',
        description="""
        Array of the fitted energies corresponding to each volume.
        """,
    )

    bulk_modulus = Quantity(
        type=np.float64,
        shape=[],
        unit='pascal',
        description="""
        Calculated value of the bulk modulus by fitting the volume-energy data.
        """,
    )

    bulk_modulus_derivative = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Calculated value of the pressure derivative of the bulk modulus.
        """,
    )

    equilibrium_volume = Quantity(
        type=np.float64,
        shape=[],
        unit='m ** 3',
        description="""
        Calculated value of the equilibrium volume by fitting the volume-energy data.
        """,
    )

    equilibrium_energy = Quantity(
        type=np.float64,
        shape=[],
        unit='joule',
        description="""
        Calculated value of the equilibrium energy by fitting the volume-energy data.
        """,
    )

    rms_error = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Root-mean squared value of the error in the fitting.
        """,
    )


class EquationOfStateResults(SimulationWorkflowResults):
    _label = 'EquationOfState workflow results'

    n_points = Quantity(
        type=np.int32,
        shape=[],
        description="""
        Number of volume-energy pairs in data.
        """,
    )

    volumes = Quantity(
        type=np.float64,
        shape=['n_points'],
        unit='m ** 3',
        description="""
        Array of volumes per atom for which the energies are evaluated.
        """,
    )

    energies = Quantity(
        type=np.float64,
        shape=['n_points'],
        unit='joule',
        description="""
        Array of energies corresponding to each volume.
        """,
    )

    eos_fit = SubSection(sub_section=EOSFit.m_def, repeats=True)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if self.n_points is None:
            try:
                self.n_points = len(archive.data.outputs)
            except Exception:
                logger.error('No Outputs found.')

        if self.energies is None:
            try:
                energies = [
                    outputs.total_energies[-1].value.to('joule').magnitude
                    for outputs in archive.data.outputs
                ]
                if energies:
                    self.energies = energies
            except Exception:
                logger.error('Total energy not found in outputs.')

        if self.volumes is None:
            try:
                volumes = []
                for system in archive.data.model_system:
                    lattice_vectors = None
                    for cell in system.cell:
                        if cell.lattice_vectors is not None:
                            lattice_vectors = cell.lattice_vectors.to('m').magnitude
                            break
                    volumes.append(get_volume(lattice_vectors))
                if volumes:
                    self.volumes = volumes
            except Exception:
                logger.error('Error getting volume from model_system.')
                return

        to_fit = self.energies is not None and self.volumes is not None

        if to_fit and not (self.n_points == len(self.energies) == len(self.volumes)):
            logger.error('Inconsistent size of energies and volumes.')
            to_fit = False

        if not self.eos_fit and to_fit:
            # convert to ase units in order for function optimization to work
            volumes = self.volumes.to('angstrom ** 3').magnitude
            energies = self.energies.to('eV').magnitude
            for function_name, ase_name in FUNCTION_NAMES.items():
                try:
                    eos = aseEOS(volumes, energies, ase_name)
                    eos.fit()
                    fitted_energies = eos.func(volumes, *eos.eos_parameters)
                    rms_error = np.sqrt(np.mean((fitted_energies - energies) ** 2))
                    eos_fit = EOSFit(
                        function_name=function_name,
                        fitted_energies=fitted_energies * ureg.eV,
                        bulk_modulus=eos.B * ureg.eV / ureg.angstrom**3,
                        equilibrium_volume=eos.v0 * ureg.angstrom**3,
                        equilibrium_energy=eos.e0 * ureg.eV,
                        rms_error=rms_error,
                    )
                    self.eos_fit.append(eos_fit)
                except Exception:
                    logger.warning('EOS fit unsuccesful.')


class EquationOfState(ParallelWorkflow):
    """
    Definitions for equation of state workflow.
    """

    _task_label = 'Volume'

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = EquationOfStateModel()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = EquationOfStateResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)


m_package.__init_metainfo__()
