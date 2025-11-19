from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.datamodel import ArchiveSection
from nomad.metainfo import Quantity, SubSection

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties import (
    AbsorptionSpectrum,
    ChemicalPotential,
    CrystalFieldSplitting,
    ElectronicBandGap,
    ElectronicBandStructure,
    ElectronicDensityOfStates,
    ElectronicEigenvalues,
    ElectronicGreensFunction,
    ElectronicSelfEnergy,
    FermiSurface,
    HoppingMatrix,
    HybridizationFunction,
    KineticEnergy,
    Occupancy,
    Permittivity,
    PotentialEnergy,
    QuasiparticleWeight,
    RadiusOfGyration,
    Temperature,
    TotalEnergy,
    TotalForce,
    XASSpectrum,
)

from .common import SimulationTime


# I don't think this should live here. 
# TODO find a new home
class SCFStep(ArchiveSection):
    """
    Data recorded at each step of a self-consistent DFT calculation.
    """

    duration = Quantity(
        type=float,
        unit='s',
        description="""
        Time spent at this SCF step.
        """,
    )

    # Placeholder for code specific quantites - these could be a dictionary
    # TODO MK: ask JFR how this is done
    code_specific_quantities = SubSection(sub_section=ArchiveSection.m_def, repeats=True)

    # Placeholder for the total energy and contributions when it is available as a physical property
    # TODO add physical property
    energy_total = Quantity(
        type=float,
        unit='joule',
        description="""
        Total energy in this SCF step.
        """
    )


class Outputs(SimulationTime):
    """
    Output properties of a simulation. This base class can be used for inheritance in any of the output properties
    defined in this schema.

    It contains references to the specific sections used to obtain the output properties, as well as
    information if the output `is_derived` from another output section or directly parsed from the simulation output files.
    """

    normalizer_level = 2

    model_system_ref = Quantity(
        type=ModelSystem,
        description="""
        Reference to the `ModelSystem` section in which the output physical properties were calculated.
        """,
    )

    model_method_ref = Quantity(
        type=ModelMethod,
        description="""
        Reference to the `ModelMethod` section containing the details of the mathematical
        model with which the output physical properties were calculated.
        """,
    )

    absorption_spectra = SubSection(sub_section=AbsorptionSpectrum.m_def, repeats=True)

    chemical_potentials = SubSection(sub_section=ChemicalPotential.m_def, repeats=True)

    crystal_field_splittings = SubSection(
        sub_section=CrystalFieldSplitting.m_def, repeats=True
    )

    electronic_band_gaps = SubSection(sub_section=ElectronicBandGap.m_def, repeats=True)

    electronic_band_structures = SubSection(
        sub_section=ElectronicBandStructure.m_def, repeats=True
    )

    electronic_dos = SubSection(
        sub_section=ElectronicDensityOfStates.m_def, repeats=True
    )

    electronic_eigenvalues = SubSection(
        sub_section=ElectronicEigenvalues.m_def, repeats=True
    )

    electronic_greens_functions = SubSection(
        sub_section=ElectronicGreensFunction.m_def, repeats=True
    )

    electronic_self_energies = SubSection(
        sub_section=ElectronicSelfEnergy.m_def, repeats=True
    )

    fermi_surfaces = SubSection(sub_section=FermiSurface.m_def, repeats=True)

    hopping_matrices = SubSection(sub_section=HoppingMatrix.m_def, repeats=True)

    hybridization_functions = SubSection(
        sub_section=HybridizationFunction.m_def, repeats=True
    )

    kinetic_energies = SubSection(sub_section=KineticEnergy.m_def, repeats=True)

    occupancies = SubSection(sub_section=Occupancy.m_def, repeats=True)

    permittivities = SubSection(sub_section=Permittivity.m_def, repeats=True)

    potential_energies = SubSection(sub_section=PotentialEnergy.m_def, repeats=True)

    quasiparticle_weights = SubSection(
        sub_section=QuasiparticleWeight.m_def, repeats=True
    )

    radii_of_gyration = SubSection(sub_section=RadiusOfGyration.m_def, repeats=True)

    temperatures = SubSection(sub_section=Temperature.m_def, repeats=True)

    #TODO I think this can be deleted in favor of scf_steps
    total_energies = SubSection(sub_section=TotalEnergy.m_def, repeats=True)

    total_forces = SubSection(sub_section=TotalForce.m_def, repeats=True)

    xas_spectra = SubSection(sub_section=XASSpectrum.m_def, repeats=True)

    scf_steps = SubSection(sub_section=SCFStep.m_def, repeats=True)

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    def extract_spin_polarized_property(
        self, property_name: str
    ) -> list[PhysicalProperty]:
        """
        Extracts the spin-polarized properties if present from the property name and returns them as a list of two elements in
        which each element refers to each `spin_channel`. If the return list is empty, it means that the simulation is not
        spin-polarized (i.e., `spin_channel` is not defined).

        Args:
            property_name (str): The name of the property to be extracted.

        Returns:
            (list[PhysicalProperty]): The list of spin-polarized properties.
        """
        spin_polarized_properties = []
        properties = getattr(self, property_name)
        for prop in properties:
            if prop.spin_channel is None:
                continue
            spin_polarized_properties.append(prop)
        return spin_polarized_properties

    def set_model_system_ref(self) -> ModelSystem | None:
        """
        Provide a suggested `ModelSystem` that corresponds to the output collection.

        Returns:
            (Optional[ModelSystem]): corresponding `ModelSystem`. `None` if there is no such section.
        """
        if self.m_parent is not None:
            model_systems = self.m_parent.model_system
            outputs = self.m_parent.outputs
            if (
                isinstance(model_systems, list)
                and isinstance(outputs, list)
                and len(model_systems) == len(outputs)
                and len(model_systems) > 0
            ):
                return model_systems[self.m_parent_index]
        return None

    def set_model_method_ref(self) -> ModelMethod | None:
        """
        Set the reference to the last `ModelMethod` if this is not set in the output. This is only
        valid if there is only one `ModelMethod` in the parent section.

        Returns:
            (Optional[ModelMethod]): The reference to the last `ModelMethod`.
        """
        if self.m_parent is not None:
            model_methods = self.m_parent.model_method
            if model_methods is not None and len(model_methods) == 1:
                return model_methods[-1]
        return None

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Set ref to the last `ModelSystem` if this is not set in the output
        if self.model_system_ref is None:
            self.model_system_ref = self.set_model_system_ref()

        # Set ref to the last `ModelMethod` if this is not set in the output
        if self.model_method_ref is None:
            self.model_method_ref = self.set_model_method_ref()


class WorkflowOutputs(Outputs):
    """
    This section contains output properties that depend on a single system, but were
    calculated as part of a workflow (e.g., the energies from a geometry optimization),
    and thus may include step information.
    """

    step = Quantity(
        type=np.int32,
        description="""
        The step number with respect to the workflow.
        """,
    )

    # TODO add this in when we link to nomad-simulations-workflow schema
    # ? check potential circular imports problems when the nomad-simulations-workflow schema is transferred here
    # workflow_ref = Quantity(
    #     type=SimulationWorkflow,
    #     description="""
    #     Reference to the `SelfConsistency` section that defines the numerical settings to converge the
    #     output property.
    #     """,
    # )


class TrajectoryOutputs(WorkflowOutputs):
    """
    This section contains output properties that depend on a single system, but were
    calculated as part of a trajectory (e.g., temperatures from a molecular dynamics
    simulation), and thus may include time information.
    """

    time = Quantity(
        type=np.float64,
        unit='ps',
        description="""
        The elapsed simulated physical time since the start of the trajectory.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
