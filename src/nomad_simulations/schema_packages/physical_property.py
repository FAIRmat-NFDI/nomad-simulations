from functools import wraps
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
from nomad import utils
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.annotations import ELNAnnotation
from nomad.datamodel.metainfo.basesections import Entity
from nomad.metainfo import (
    URL,
    MEnum,
    Quantity,
    Reference,
    SectionProxy,
    SubSection,
)
from nomad.metainfo.metainfo import Dimension, DirectQuantity, _placeholder_quantity

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
    when inheriting from `PhysicalProperty`. It also contains `rank`, to define the tensor rank of the physical property, and
    `variables`, to define the variables over which the physical property varies (see variables.py). This class can also store several
    string identifiers and quantities for referencing and establishing the character of a physical property.
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
    )  # ?

    label = Quantity(
        type=str,
        description="""
        Label for additional classification of the physical property. Example: an `ElectronicBandGap`
        can be labeled as `'DFT'` or `'GW'` depending on the methodology used to calculate it.
        """,
        # ! add more examples in the description to improve the understanding of this quantity
    )  # ?

    variables = SubSection(sub_section=Variables.m_def, repeats=True)

    value: Any = None

    # * `value` must be overwritten in the derived classes defining its type, unit, and description
    _base_value: Quantity = _placeholder_quantity

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
    )  # TODO: move to numerical settings

    self_consistency_ref = Quantity(
        type=SelfConsistency,
        description="""
        Reference to the `SelfConsistency` section that defines the numerical settings to converge the
        physical property (see numerical_settings.py).
        """,
    )

    @property
    def variables_shape(self) -> list[int]:
        """
        Shape of the variables over which the physical property varies. This is extracted from
        `Variables.n_points` and appended in a list.

        Example, a physical property which varies with `Temperature` and `ElectricField` will
        return `variables_shape = [n_temperatures, n_electric_fields]`.

        Returns:
            (list): The shape of the variables over which the physical property varies.
        """
        if self.variables:
            return [v.get_n_points(logger) for v in self.variables]  # ! TODO: support any variable shape, not just vectors
        return []
    
    @property
    def rank(self) -> list[int]:
        """
        Rank of the physical property. This quantity is related with the order of the tensor of `value`.

        Example: a physical property which is a 3D vector will have `rank=[3]`.

        Returns:
            (list): The rank of the physical property.
        """
        if (base_value := self.m_def.all_quantities.get('_base_value')):
            if isinstance(base_value.shape, list):
                return base_value.shape
            else:
                return []
        raise ValueError('The `_base_value` quantity is not defined.')

    @property
    def full_shape(self) -> list:
        """
        Full shape of the physical property. This quantity is calculated as a concatenation of the `variables_shape`
        and `rank`:

            `full_shape = variables_shape + rank`

        where `rank` is passed as an attribute of the `PhysicalProperty` and is related with the order of
        the tensor of `value`, and `variables_shape` is obtained from the property-decorated function `variables_shape()`
        and is related with the shapes of the `variables` over which the physical property varies.

        Example: a physical property which is a 3D vector and varies with `variables=[Temperature, ElectricField]`
        will have `rank=[3]`, `variables_shape=[n_temperatures, n_electric_fields]`, and thus
        `full_shape=[n_temperatures, n_electric_fields, 3]`.

        Returns:
            (list): The full shape of the physical property.
        """
        return self.variables_shape + self.rank

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)

        # Checking if IRI is defined
        if not self.iri:
            logger.warning(
                'The used property is not defined in the FAIRmat taxonomy (https://fairmat-nfdi.github.io/fairmat-taxonomy/).'
            )  # ?

    def __setattr__(self, name: str, value: Any) -> None:
        # redirect from `_base_value` to `value`
        if name == '_base_value':
            if not isinstance(value, str):
                self.value = value
            elif not value.startswith('m_'):
                self.value = value
        else:
            super().__setattr__(name, value)

    def _is_derived(self) -> bool:  # ?
        """
        Resolves whether the physical property is derived or not.

        Returns:
            (bool): The flag indicating whether the physical property is derived or not.
        """
        if self.physical_property_ref is not None:
            return True
        return False

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # self.is_derived = self._is_derived()  # ?

        try:
            if self.value is not None:
                value = self.value
            elif self._base_value is not None:
                value = self._base_value
            else:
                value = None
        except AttributeError:
            raise AttributeError('The `value` or `_base_value` is not defined at the _quantity_ level.')

        self.m_def.quantities.append(
            Quantity(
                name='value',
                shape=self.full_shape,
                type=self.m_def.all_quantities['_base_value'].type,
                unit=self.m_def.all_quantities['_base_value'].unit,
                description=self.m_def.all_quantities['_base_value'].description,
            )
        )
        if value is not None:  # ! pin down type
            self.value = value.to(self.m_def.all_quantities['value'].unit).magnitude


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
        a_eln=ELNAnnotation(component='ReferenceEditQuantity'),
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)
        if not self.name:
            self.name = self.get('model_method_ref').get('name')
