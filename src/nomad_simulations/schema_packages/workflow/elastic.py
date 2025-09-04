import numpy as np
from nomad.datamodel import EntryArchive
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.workflow import Link, TaskReference
from nomad.metainfo import (
    MEnum,
    Quantity,
    Reference,
    SchemaPackage,
    Section,
    SubSection,
)
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.general import Program
from nomad_simulations.schema_packages.utils import log

from .general import INCORRECT_N_TASKS, SimulationWorkflow, SimulationWorkflowModel
from .thermodynamics import ThermodynamicsResults

m_package = SchemaPackage()


class ElasticModel(SimulationWorkflowModel):
    _label = 'Elastic model'

    program = Quantity(
        type=Reference(Program),
        shape=[],
        description="""
        Program used to calculate the energies.
        """,
    )

    calculation_method = Quantity(
        type=str,
        shape=[],
        description="""
        Method used to calculate elastic constants, can either be energy or stress.
        """,
    )

    elastic_constants_order = Quantity(
        type=int,
        shape=[],
        description="""
        Order of the calculated elastic constants.
        """,
    )

    fitting_error_maximum = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Maximum error in polynomial fit.
        """,
    )

    strain_maximum = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Maximum strain applied to crystal.
        """,
    )


class StrainDiagrams(ArchiveSection):
    """
    Section containing the information regarding the elastic strains.
    """

    m_def = Section(validate=False)

    type = Quantity(
        type=str,
        shape=[],
        description="""
        Kind of strain diagram. Possible values are: energy; cross-validation (cross-
        validation error); d2E (second derivative of the energy wrt the strain)
        """,
    )

    n_eta = Quantity(
        type=np.int32,
        shape=[],
        description="""
        Number of strain values used in the strain diagram
        """,
    )

    n_deformations = Quantity(
        type=np.int32,
        shape=[],
        description="""
        Number of deformations.
        """,
    )

    value = Quantity(
        type=np.float64,
        shape=['n_deformations', 'n_eta'],
        description="""
        Values of the energy(units:J)/d2E(units:Pa)/cross-validation (depending on the
        value of strain_diagram_type)
        """,
    )

    eta = Quantity(
        type=np.float64,
        shape=['n_deformations', 'n_eta'],
        description="""
        eta values used the strain diagrams
        """,
    )

    stress_voigt_component = Quantity(
        type=np.int32,
        shape=[],
        description="""
        Voigt component corresponding to the strain diagram
        """,
    )

    polynomial_fit_order = Quantity(
        type=np.int32,
        shape=[],
        description="""
        Order of the polynomial fit
        """,
    )


class ElasticResults(ThermodynamicsResults):
    _label = 'Elastic results'

    n_deformations = Quantity(
        type=np.int32,
        shape=[],
        description="""
        Number of deformed structures used to calculate the elastic constants. This is
        determined by the symmetry of the crystal.
        """,
    )

    deformation_types = Quantity(
        type=np.str_,
        shape=['n_deformations', 6],
        description="""
        deformation types
        """,
    )

    n_strains = Quantity(
        type=np.int32,
        shape=[],
        description="""
        number of equally spaced strains applied to each deformed structure, which are
        generated between the maximum negative strain and the maximum positive one.
        """,
    )

    is_mechanically_stable = Quantity(
        type=bool,
        shape=[],
        description="""
        Indicates if structure is mechanically stable from the calculated values of the
        elastic constants.
        """,
    )

    elastic_constants_notation_matrix_second_order = Quantity(
        type=np.str_,
        shape=[6, 6],
        description="""
        Symmetry of the second-order elastic constant matrix in Voigt notation
        """,
    )

    elastic_constants_matrix_second_order = Quantity(
        type=np.float64,
        shape=[6, 6],
        unit='pascal',
        description="""
        2nd order elastic constant (stiffness) matrix in pascals
        """,
    )

    elastic_constants_matrix_third_order = Quantity(
        type=np.float64,
        shape=[6, 6, 6],
        unit='pascal',
        description="""
        3rd order elastic constant (stiffness) matrix in pascals
        """,
    )

    compliance_matrix_second_order = Quantity(
        type=np.float64,
        shape=[6, 6],
        unit='1 / pascal',
        description="""
        Elastic compliance matrix in 1/GPa
        """,
    )

    elastic_constants_gradient_matrix_second_order = Quantity(
        type=np.float64,
        shape=[18, 18],
        unit='newton',
        description="""
        gradient of the 2nd order elastic constant (stiffness) matrix in newton
        """,
    )

    bulk_modulus_voigt = Quantity(
        type=np.float64,
        shape=[],
        unit='pascal',
        description="""
        Voigt bulk modulus
        """,
    )

    shear_modulus_voigt = Quantity(
        type=np.float64,
        shape=[],
        unit='pascal',
        description="""
        Voigt shear modulus
        """,
    )

    bulk_modulus_reuss = Quantity(
        type=np.float64,
        shape=[],
        unit='pascal',
        description="""
        Reuss bulk modulus
        """,
    )

    shear_modulus_reuss = Quantity(
        type=np.float64,
        shape=[],
        unit='pascal',
        description="""
        Reuss shear modulus
        """,
    )

    bulk_modulus_hill = Quantity(
        type=np.float64,
        shape=[],
        unit='pascal',
        description="""
        Hill bulk modulus
        """,
    )

    shear_modulus_hill = Quantity(
        type=np.float64,
        shape=[],
        unit='pascal',
        description="""
        Hill shear modulus
        """,
    )

    young_modulus_voigt = Quantity(
        type=np.float64,
        shape=[],
        unit='pascal',
        description="""
        Voigt Young modulus
        """,
    )

    poisson_ratio_voigt = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Voigt Poisson ratio
        """,
    )

    young_modulus_reuss = Quantity(
        type=np.float64,
        shape=[],
        unit='pascal',
        description="""
        Reuss Young modulus
        """,
    )

    poisson_ratio_reuss = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Reuss Poisson ratio
        """,
    )

    young_modulus_hill = Quantity(
        type=np.float64,
        shape=[],
        unit='pascal',
        description="""
        Hill Young modulus
        """,
    )

    poisson_ratio_hill = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Hill Poisson ratio
        """,
    )

    elastic_anisotropy = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Elastic anisotropy
        """,
    )

    pugh_ratio_hill = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Pugh ratio defined as the ratio between the shear modulus and bulk modulus
        """,
    )

    debye_temperature = Quantity(
        type=np.float64,
        shape=[],
        unit='kelvin',
        description="""
        Debye temperature
        """,
    )

    speed_sound_transverse = Quantity(
        type=np.float64,
        shape=[],
        unit='meter / second',
        description="""
        Speed of sound along the transverse direction
        """,
    )

    speed_sound_longitudinal = Quantity(
        type=np.float64,
        shape=[],
        unit='meter / second',
        description="""
        Speed of sound along the longitudinal direction
        """,
    )

    speed_sound_average = Quantity(
        type=np.float64,
        shape=[],
        unit='meter / second',
        description="""
        Average speed of sound
        """,
    )

    eigenvalues_elastic = Quantity(
        type=np.float64,
        shape=[6],
        unit='pascal',
        description="""
        Eigenvalues of the stiffness matrix
        """,
    )

    strain_diagrams = SubSection(sub_section=StrainDiagrams.m_def, repeats=True)


class Elastic(SimulationWorkflow):
    """
    Definitions for an elastic workflow.
    """

    _task_label = 'Deformation'

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = ElasticModel()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = ElasticResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)

        if len(self.tasks) < 2:
            logger.error(INCORRECT_N_TASKS)
            return

        # assign inputs to deformation calculations
        for n, task in enumerate(self.tasks[:-1]):
            if not task.name:
                task.name = f'Deformation calculation for supercell {n}'
            task.inputs.extend([inp for inp in self.inputs if inp not in task.inputs])

        # assign outputs of deformation calculation as input to elastic task
        self.tasks[-1].inputs = [
            Link(
                name='Linked task',
                section=task.task if isinstance(task, TaskReference) else task,
            )
            for task in self.tasks[:-1]
        ]

        # add elastic task oututs to outputs
        self.outputs.extend(
            [out for out in self.tasks[-1].outputs if out not in self.outputs]
        )

        if not self.tasks[-1].name:
            self.tasks[-1].name = 'Elastic calculation'


m_package.__init_metainfo__()
