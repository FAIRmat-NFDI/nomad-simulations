import numpy as np
from nomad.datamodel import EntryArchive, SubSection
from nomad.metainfo import Quantity, SchemaPackage, Reference
from nomad.datamodel.hdf5 import HDF5Dataset
from structlog.stdlib import BoundLogger
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.workflow.general import SimulationWorkflowOutputs


class TrajectoryProperty(PhysicalProperty):
    """
    Generic section containing information about a calculation of any observable
    defined and stored at each individual frame of a trajectory.
    """

    n_frames = Quantity(
        type=int,
        shape=[],
        description="""
        Number of frames for which the observable is stored.
        """,
    )

    frames = Quantity(
        type=np.int32,
        shape=['n_frames'],
        description="""
        Frames for which the observable is stored.
        """,
    )

    times = Quantity(
        type=np.float64,
        shape=['n_frames'],
        unit='s',
        description="""
        Times for which the observable is stored.
        """,
    )


class Temperatures(TrajectoryProperty):
    """
    Temperature as a function of time.
    """

    _label = 'Temperature trajectory'

    value = Quantity(
        type=np.float64,
        shape=['*'],
        unit='kelvin',
        description="""
        Specifies the temperature over a series of frames/steps.
        """,
    )


class Pressures(TrajectoryProperty):
    """
    Pressure as a function of time.
    """

    _label = 'Pressure trajectory'

    value = Quantity(
        type=np.float64,
        shape=['*'],
        unit='pascal',
        description="""
        Specifies the pressure over a series of frames/steps.
        """,
    )


# TODO Rg + TrajectoryPropery should be removed from workflow. All properties dependent on a single configuration should be store in calculation
class RadiiOfGyration(TrajectoryProperty):
    """
    Section containing information about the calculation of
    radius of gyration (Rg).
    """

    _rg_results = None

    # TODO remove or replace with system ref if nec
    # atomsgroup_ref = Quantity(
    #     type=Reference(AtomsGroup.m_def),
    #     shape=[1],
    #     description="""
    #     References to the atoms_group section containing the molecule for which Rg was calculated.
    #     """,
    # )

    value = Quantity(
        type=np.float64,
        shape=['n_frames'],
        unit='m',
        description="""
        Values of the property.
        """,
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if self._rg_results:
            self.type = self._rg_results.get('type')
            self.label = self._rg_results.get('label')
            # TODO Fix this assignment fails with TypeError
            try:
                self.atomsgroup_ref = [self._rg_results.get('atomsgroup_ref')]
            except Exception:
                pass
            self.n_frames = self._rg_results.get('n_frames')
            self.times = self._rg_results.get('times')
            self.value = self._rg_results.get('value')


class FreeEnergyCalculations(TrajectoryProperty):
    """
    Section containing information regarding the instantaneous (i.e., for a single configuration)
    values of free energies calculated via thermodynamic perturbation.
    The values stored are actually infinitesimal changes in the free energy, determined as derivatives
    of the Hamiltonian with respect to the coupling parameter (lambda) defining each state for the perturbation.
    """

    method_ref = Quantity(
        type=Reference(
            'nomad_simulations.schema_packages.workflow.molecular_dynamics.FreeEnergyCalculationParameters'
        ),
        shape=[],
        description="""
        Links the free energy results with the method parameters.
        """,
    )

    lambda_index = Quantity(
        type=int,
        shape=[],
        description="""
        Index of the lambda state for the present simulation within the free energy calculation workflow.
        I.e., lambda = method_ref.lambdas.values[lambda_index]
        """,
    )

    n_states = Quantity(
        type=int,
        shape=[],
        description="""
        Number of states defined for the interpolation of the system, as indicate in `method_ref`.
        """,
    )

    value_total_energy_magnitude = Quantity(
        type=HDF5Dataset,
        shape=[],
        unit='joule',
        description="""
        Value of the total energy for the present lambda state. The expected dimensions are ["n_frames"].
        This quantity is a reference to the data (file+path), which is stored in an HDF5 file for efficiency.
        """,
    )

    value_PV_energy_magnitude = Quantity(
        type=HDF5Dataset,
        shape=[],
        unit='joule',
        description="""
        Value of the pressure-volume energy (i.e., P*V) for the present lambda state. The expected dimensions are ["n_frames"].
        This quantity is a reference to the data (file+path), which is stored in an HDF5 file for efficiency.
        """,
    )

    value_total_energy_differences_magnitude = Quantity(
        type=HDF5Dataset,
        shape=[],
        unit='joule',
        description="""
        Values correspond to the difference in total energy between each specified lambda state
        and the reference state, which corresponds to the value of lambda of the current simulation.
        The expected dimensions are ["n_frames", "n_states"].
        This quantity is a reference to the data (file+path), which is stored in an HDF5 file for efficiency.
        """,
    )

    value_total_energy_derivative_magnitude = Quantity(
        type=HDF5Dataset,
        shape=[],
        unit='joule',  # TODO check this unit
        description="""
        Value of the derivative of the total energy with respect to lambda, evaluated for the current
        lambda state. The expected dimensions are ["n_frames"].
        This quantity is a reference to the data (file+path), which is stored in an HDF5 file for efficiency.
        """,
    )


class SerialWorkflowOutputs(SimulationWorkflowOutputs):
    _label = 'Thermodynamics ouputs'

    temperatures = SubSection(sub_section=Temperatures.m_def, repeats=True)

    pressures = SubSection(sub_section=Pressures.m_def, repeats=True)

    radii_of_gyration = SubSection(sub_section=RadiiOfGyration.m_def, repeats=True)

    free_energy_calculations = SubSection(
        sub_section=FreeEnergyCalculations.m_def, repeats=True
    )
