from functools import wraps
from typing import TYPE_CHECKING, Optional

import numpy as np
from nomad import utils
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.basesections.v2 import Entity
from nomad.metainfo import URL, MEnum, Quantity, Reference, SectionProxy, SubSection

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.model_method import BaseModelMethod
from nomad_simulations.schema_packages.numerical_settings import SelfConsistency
from nomad_simulations.schema_packages.variables import Variables

# We add `logger` for the `validate_quantity_wrt_value` decorator
logger = utils.get_logger(__name__)


def validate_quantity_wrt_value(name: str = ''):
    """
    Decorator to validate the existence of a quantity and its shape with respect to the `PhysicalProperty.value`
    before calling a method. An example can be found in the module `properties/band_structure.py` for the method
    `ElectronicEigenvalues.order_eigenvalues()`.

    Args:
        name (str, optional): The name of the `quantity` to validate. Defaults to ''.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Checks if `quantity` is defined
            quantity = getattr(self, name, None)
            if quantity is None or len(quantity) == 0:
                logger.warning(f'The quantity `{name}` is not defined.')
                return False

            # Checks if `value` exists and has the same shape as `quantity`
            value = getattr(self, 'value', None)
            if value is None:
                logger.warning('The quantity `value` is not defined.')
                return False
            if value is not None and value.shape != quantity.shape:
                logger.warning(
                    f'The shape of the quantity `{name}` does not match the shape of the `value`.'
                )
                return False

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


class PhysicalProperty(ArchiveSection):
    """
    A base section used to define the physical properties obtained in a simulation, experiment, or in a post-processing
    analysis. The main quantity of the `PhysicalProperty` is `value`, whose instantiation has to be overwritten in the derived classes
    when inheriting from `PhysicalProperty`. It contains `variables`, to define the variables over which the physical property varies (see variables.py).
    This class can also store several string identifiers and quantities for referencing and establishing the character of a physical property.
    """

    # TODO add `errors`
    # TODO add `smearing`

    name = Quantity(
        type=str,
        description="""
        Name of the physical property. Example: `'ElectronicBandGap'`.
        """,
    )

    iri = Quantity(
        type=URL,
        description="""
        Internationalized Resource Identifier (IRI) of the physical property defined in the FAIRmat
        taxonomy, https://fairmat-nfdi.github.io/fairmat-taxonomy/.
        """,
    )

    source = Quantity(
        type=MEnum('simulation', 'measurement', 'analysis'),
        default='simulation',
        description="""
        Source of the physical property. This quantity is related with the `Activity` performed to obtain the physical
        property. Example: an `ElectronicBandGap` can be obtained from a `'simulation'` or in a `'measurement'`.
        """,
    )

    type = Quantity(
        type=str,
        description="""
        Type categorization of the physical property. Example: an `ElectronicBandGap` can be `'direct'`
        or `'indirect'`.
        """,
        # ! add more examples in the description to improve the understanding of this quantity
    )

    label = Quantity(
        type=str,
        description="""
        Label for additional classification of the physical property. Example: an `ElectronicBandGap`
        can be labeled as `'DFT'` or `'GW'` depending on the methodology used to calculate it.
        """,
        # ! add more examples in the description to improve the understanding of this quantity
    )

    # variables = SubSection(sub_section=Variables.m_def, repeats=True)

    # * `value` must be overwritten in the derived classes defining its type, unit, and description
    # TODO use abstract to enforce policy?
    value: Quantity = None

    entity_ref = Quantity(
        type=Entity,
        description="""
        Reference to the entity that the physical property refers to. Examples:
            - a simulated physical property might refer to the macroscopic system or instead of a specific atom in the unit
            cell. In the first case, `outputs.model_system_ref` (see outputs.py) will point to the `ModelSystem` section,
            while in the second case, `entity_ref` will point to `AtomsState` section (see atoms_state.py).
        """,
    )

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
    )

    self_consistency_ref = Quantity(
        type=SelfConsistency,
        description="""
        Reference to the `SelfConsistency` section that defines the numerical settings to converge the
        physical property (see numerical_settings.py).
        """,
    )

    # @property
    # def variables_shape(self) -> Optional[list]:
    #    """
    #    Shape of the variables over which the physical property varies. This is extracted from
    #    `Variables.n_points` and appended in a list.
    #
    #    Example, a physical property which varies with `Temperature` and `ElectricField` will
    #    return `variables_shape = [n_temperatures, n_electric_fields]`.
    #
    #    Returns:
    #        (list): The shape of the variables over which the physical property varies.
    #    """
    #    if self.variables is not None:
    #        return [v.get_n_points(logger) for v in self.variables]
    #    return []

    @property
    def full_shape(self) -> list[int]:
        """
        Full shape of the physical property. This quantity is calculated as a concatenation of the `variables_shape`
        and `value.shape`:

            `full_shape = variables_shape + value.shape`

        Example: a physical property which is a 3D vector and varies with `variables=[Temperature, ElectricField]`
        will have `value.shape=[3]`, `variables_shape=[n_temperatures, n_electric_fields]`, and thus
        `full_shape=[n_temperatures, n_electric_fields, 3]`.

        Returns:
            (list): The full shape of the physical property.
        """
        value_shape = self.value.shape if self.value is not None else []
        # return self.variables_shape + value_shape
        return [] + value_shape

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)
        # Checking if IRI is defined
        if self.iri is None:
            logger.warning(
                'The used property is not defined in the FAIRmat taxonomy (https://fairmat-nfdi.github.io/fairmat-taxonomy/). You can contribute there if you want to extend the list of available materials properties.'
            )

    def __setattr__(self, name, value):
        if name == 'value':
            try:
                value = np.array(value)
                # self.__class__.value.shape = ['*'] * value.ndim
            except Exception:
                pass
        return super().__setattr__(name, value)

    def _is_derived(self) -> bool:
        """
        Resolves whether the physical property is derived or not.

        Returns:
            (bool): The flag indicating whether the physical property is derived or not.
        """
        if self.physical_property_ref is not None:
            return True
        return False

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        self.is_derived = self._is_derived()


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
            self.name = self.get('model_method_ref').get('name')
