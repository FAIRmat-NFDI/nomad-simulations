from nomad import utils
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.datamodel.metainfo.basesections.v2 import Entity
from nomad.metainfo import URL, MEnum, Quantity, Reference, SectionProxy

from nomad_simulations.schema_packages.model_method import BaseModelMethod
from nomad_simulations.schema_packages.numerical_settings import SelfConsistency

logger = utils.get_logger(__name__)

class PhysicalProperty(PlotSection):
    """
    A base section for computational output properties,
    containing all (meta)data relevant for visualization.
    Define and use `value` when the data corresponds with the titular section property.
    May also contain partitions as subsections.
    """

    name = Quantity(
        type=str,
        description="""
        Name of the physical property. Example: `'ElectronicBandGap'`.
        """,
    )

    iri = Quantity(
        type=URL,
        default='',
        description="""
        Internationalized Resource Identifier (IRI) pointing to a definition,
        typically within a larger, ontological framework.
        """,
    )

    source = Quantity(
        type=MEnum('simulation', 'measurement', 'analysis'),
        default='simulation',
        description="""
        Source of the physical property. This quantity is related with the `Activity` performed to obtain the physical
        property. Example: an `ElectronicBandGap` can be obtained from a `'simulation'` or in a `'measurement'`.
        """,
    )  # ? unused

    type = Quantity(
        type=str,
        description="""
        Type categorization of the physical property. Example: an `ElectronicBandGap` can be `'direct'`
        or `'indirect'`.
        """,
    )

    label = Quantity(
        type=str,
        description="""
        Label for additional classification of the physical property. Example: an `ElectronicBandGap`
        can be labeled as `'DFT'` or `'GW'` depending on the methodology used to calculate it.
        """,
    )

    value: Quantity = None

    entity_ref = Quantity(
        type=Entity,
        description="""
        Reference to the entity that the physical property refers to. Examples:
            - a simulated physical property might refer to the macroscopic system or instead of a specific atom in the unit
            cell. In the first case, `outputs.model_system_ref` (see outputs.py) will point to the `ModelSystem` section,
            while in the second case, `entity_ref` will point to `AtomsState` section (see atoms_state.py).
        """,
    )  # TODO: only used for electronic states, remove

    physical_property_ref = Quantity(
        type=Reference(SectionProxy('PhysicalProperty')),
        description="""
        Reference to the `PhysicalProperty` section from which the physical property was derived. If `physical_property_ref`
        is populated, the quantity `is_derived` is set to True via normalization.
        """,
    )

    is_derived = Quantity(
        type=bool,
        default=False,
        description="""
        Flag indicating whether the physical property is derived from other physical properties. We make
        the distinction between directly parsed and derived physical properties:
            - Directly parsed: the physical property is directly parsed from the simulation output files.
            - Derived: the physical property is derived from other physical properties. No extra numerical settings
                are required to calculate the physical property.
        """,
    )

    is_scf_converged = Quantity(
        type=bool,
        description="""
        Flag indicating whether the physical property is converged or not after a SCF process. This quantity is connected
        with `SelfConsistency` defined in the `numerical_settings.py` module.
        """,
    )  # ? remove

    self_consistency_ref = Quantity(
        type=SelfConsistency,
        description="""
        Reference to the `SelfConsistency` section that defines the numerical settings to converge the
        physical property (see numerical_settings.py).
        """,
    )  # ? remove

    def _is_derived(self) -> bool:
        """
        Resolves whether the physical property is derived or not.

        Returns:
            (bool): The flag indicating whether the physical property is derived or not.
        """
        return self.physical_property_ref is not None
 
    def plot(self, *args, **kwargs) -> list:
        """
        Placeholder for a method to plot the physical property. This method should be overridden in derived classes
        to provide specific plotting functionality.

        Returns:
            (list): A list of figures (`PlotlyFigure`) representing the physical property.
        """
        return []

    def normalize(self, *args, **kwargs) -> None:
        self.is_derived = self._is_derived()
        super(PlotSection, self).normalize(*args, **kwargs)
        if (plot_figures := self.plot(*args, **kwargs)):
            self.figures.extend(plot_figures)
        if self.m_def.name is not None:
            self.name = self.m_def.name


class PropertyContribution(PhysicalProperty):
    """
    Abstract physical property section linking a property contribution to a contribution
    from some method.

    Abstract class for incorporating specific contributions of a physical property, while
    linking this contribution to a specific component (of class `BaseModelMethod`) of the
    over `ModelMethod` using the `model_method_ref` quantity.
    """

    model_method_ref = Quantity(
        type=BaseModelMethod,
        description="""
        Reference to the `ModelMethod` section to which the property is linked to.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)
        if not self.name:
            self.name = self.get('model_method_ref', {}).get('name')
