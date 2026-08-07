from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.datamodel import JSON, ArchiveSection
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


# MK: I don't think this should live here.
# @all: where to move this?
class SCFSteps(ArchiveSection):
    """
    Data recorded at each step of a self-consistent DFT calculation.
    """

    energies_total = Quantity(
        shape=['*'],
        type=float,
        unit='joule',
        description="""
        Total energy at each SCF step.
        """,
    )

    delta_energies_total = Quantity(
        shape=['*'],
        type=float,
        unit='joule',
        description="""
        Absolute change of total energy at each SCF step.
        """,
    )

    energy_error_estimate = Quantity(
        shape=['*'],
        type=float,
        unit='joule',
        description="""
        Estimate of the remaining error in the total energy at each SCF step,
        derived from the density residual rather than from the change of the
        total energy itself. For example, Quantum ESPRESSO's "estimated scf
        accuracy" is the Hartree self-energy of the density residual. Distinct
        from `delta_energies_total`, which is the change of the total energy
        between consecutive steps.
        """,
    )

    delta_potential_rms = Quantity(
        shape=['*'],
        type=float,
        unit='joule',
        description="""
        Root mean square of change of potential energy at each SCF step.
        """,
    )

    delta_charge_abs = Quantity(
        shape=['*'],
        type=float,
        unit='coulomb',
        description="""
        Volume-integrated absolute change of the electron density between
        consecutive SCF steps, `integral |rho_n(r) - rho_(n-1)(r)| d^3r`,
        expressed as a charge (equivalently a number of electrons). Reported by
        all-electron codes such as WIEN2k (`:DIS`). The exact norm and any
        normalization are a code-reported convention that the schema does not
        enforce.
        """,
    )

    delta_charge_density_rms = Quantity(
        shape=['*'],
        type=float,
        unit='coulomb / meter ** 3',
        description="""
        Root mean square, over real-space grid points, of the change of the
        electron density between consecutive SCF steps. Unlike `delta_charge_abs`
        the volume is retained, so this is a charge density. Reported by
        plane-wave codes such as VASP (`rms(c)`).
        """,
    )

    delta_charge_relative = Quantity(
        shape=['*'],
        type=float,
        unit='dimensionless',
        description="""
        Integrated absolute density change normalized by the electron count,
        `integral |rho_n - rho_(n-1)| d^3r / N`, hence dimensionless. Reported by
        exciting ("charge distance") and GPAW (per valence electron).
        """,
    )

    delta_density_matrix_rms = Quantity(
        shape=['*'],
        type=float,
        unit='dimensionless',
        description="""
        Root mean square of the change of the density-matrix elements `P_munu`
        (in the non-orthonormal atomic-orbital basis) between consecutive SCF
        steps. The elements are dimensionless, so is this residual. Reported by
        Gaussian-basis codes such as CRYSTAL (`tst`) and ORCA (`RMS-DP`).
        """,
    )

    delta_density_matrix_max = Quantity(
        shape=['*'],
        type=float,
        unit='dimensionless',
        description="""
        Maximum absolute change of the density-matrix elements `P_munu` between
        consecutive SCF steps; the max-norm counterpart of
        `delta_density_matrix_rms`. Reported by Gaussian-basis codes such as
        CP2K, CRYSTAL (`PX`), and ORCA (`Max-DP`).
        """,
    )

    delta_wavefunction_rms = Quantity(
        shape=['*'],
        type=float,
        unit='dimensionless',
        description="""
        Root mean square of change of wavefunction coefficients at each SCF step.
        Dimensionless quantity representing convergence of orbital coefficients.
        """,
    )

    delta_force_abs = Quantity(
        shape=['*'],
        type=float,
        unit='newton',
        description="""
        Absolute change of forces at each SCF step.
        """,
    )

    durations = Quantity(
        shape=['*'],
        type=float,
        unit='s',
        description="""
        Time spent at each SCF step.
        """,
    )

    code_specific_quantities = Quantity(
        type=JSON,
        description="""
        Code specific quantities that are recorded during SCF convergence.
        """,
    )


# TODO: Outputs should not be of type time, but the workflow should be instead?
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

    total_forces = SubSection(sub_section=TotalForce.m_def, repeats=True)

    total_energies = SubSection(sub_section=TotalEnergy.m_def, repeats=True)

    xas_spectra = SubSection(sub_section=XASSpectrum.m_def, repeats=True)

    scf_steps = SubSection(sub_section=SCFSteps.m_def, repeats=False)

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
            if model_systems is None or len(model_systems) == 0:
                return None

            if outputs and len(model_systems) == len(outputs):
                return model_systems[self.m_parent_index]

            # Prefer representative system when explicit 1-1 mapping is unavailable.
            idx = getattr(self.m_parent, 'representative_system_index', None)
            if isinstance(idx, (int, np.integer)) and 0 <= idx < len(model_systems):
                return model_systems[idx]

            # Fallback for trajectory-like archives: use the first system carrying
            # particle-state topology metadata.
            for model_system in model_systems:
                if getattr(model_system, 'particle_states', None):
                    return model_system

            # Last-resort fallback to keep downstream reference-dependent
            # normalization paths functional in mismatched-length payloads.
            return model_systems[-1]
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

    def _compute_energy_deltas(self, logger: 'BoundLogger'):
        """
        Compute `delta_energies_total` as the absolute change between consecutive
        `scf_steps.energies_total` values, i.e. the per-SCF-iteration total-energy
        series. This is the correct source for an SCF convergence measure; the
        repeating `Outputs.total_energies` holds labeled generic total energies
        (e.g. "DFT" vs "DFT + dispersion"), whose differences are not SCF deltas.
        """
        if self.scf_steps is None or self.scf_steps.energies_total is None:
            return None
        energies = self.scf_steps.energies_total
        if len(energies) < 2:
            return None
        return np.abs(np.diff(energies.magnitude)) * energies.units

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Set refs opportunistically in all contexts.
        # Some lightweight/CLI contexts can fail reference assignment depending on
        # serialization backend state, so keep this best-effort and non-fatal.
        try:
            if self.model_system_ref is None:
                self.model_system_ref = self.set_model_system_ref()
        except Exception as e:
            logger.debug(f'Could not set model_system_ref: {e}')

        try:
            # Set ref to the last `ModelMethod` if this is not set in the output
            if self.model_method_ref is None:
                self.model_method_ref = self.set_model_method_ref()
        except Exception as e:
            logger.debug(f'Could not set model_method_ref: {e}')

        # Derive `delta_energies_total` from the per-SCF `energies_total` series when the
        # parser did not provide it directly (#454).
        #
        # The other SCF residuals are deliberately NOT synthesized here. In particular
        # `delta_force_abs` (the change of forces between successive SCF iterations) cannot
        # be derived from the archive: `Outputs.total_forces` holds the final/labeled forces,
        # not a per-SCF-iteration series, so norming them would file the final force
        # magnitudes under an SCF-convergence field -- a physically different quantity (#453).
        # `delta_force_abs` and the density/potential residuals are therefore set only by
        # parsers that genuinely report them per SCF step.
        if self.scf_steps is not None and self.scf_steps.delta_energies_total is None:
            deltas = self._compute_energy_deltas(logger)
            if deltas is not None:
                self.scf_steps.delta_energies_total = deltas


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
