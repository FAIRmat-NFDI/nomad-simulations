from typing import TYPE_CHECKING

from nomad import utils
from nomad.datamodel.metainfo.basesections.v2 import Entity
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import URL, Quantity, Reference, SectionProxy, SubSection

from nomad_simulations.schema_packages.numerical_settings import SelfConsistency
from nomad_simulations.schema_packages.utils import log

logger = utils.get_logger(__name__)

if TYPE_CHECKING:
    from nomad.datamodel.metainfo import BoundLogger


class PhysicalProperty(PlotSection):
    """
    A base section for computational output properties, containing all relevant
    (meta)data. This includes support for visualization and plotting.

    - Supports the definition and use of `value` for the main property data.
    - Allows for the inclusion of contributions (e.g., via the `contribution_type` attribute and
      possible subsections), enabling representation of properties that are composed of multiple
      parts or sources.
    - Inherits from `PlotSection`, enabling direct integration with plotting and visualization tools.
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

    type = Quantity(
        type=str,
        description="""
        Type categorization of the physical property. Example: an `ElectronicBandGap` can be `'direct'`
        or `'indirect'`.
        """,
    )

    contribution_type = Quantity(
        type=str,
        default=None,
        description="""
        Type of contribution to the physical property. Hence, only applies to `contributions` instances.
        Example: `TotalEnergy` may have contributions like _kinetic_, _potential_, etc.
        """,
    )

    label = Quantity(
        type=str,
        description="""
        Label for additional classification of the physical property. Example: an `ElectronicBandGap`
        can be labeled as `'DFT'` or `'GW'` depending on the methodology used to calculate it.
        """,
    )  # TODO: specify use better

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

    physical_property_ref = Quantity(
        type=Reference(SectionProxy('PhysicalProperty')),
        description="""
        Reference to the `PhysicalProperty` section from which the physical property was derived. If `physical_property_ref`
        is populated, the quantity `is_derived` is set to True via normalization.
        """,
    )

    is_scf_converged = Quantity(
        type=bool,
        description="""
        Flag indicating whether the physical property is converged or not after a SCF process. This quantity is connected
        with `SelfConsistency` defined in the `numerical_settings.py` module.
        """,
    )  # ? tie to calculation, not individual property

    self_consistency_ref = Quantity(
        type=SelfConsistency,
        description="""
        Reference to the `SelfConsistency` section that defines the numerical settings to converge the
        physical property (see numerical_settings.py).
        """,
    )  # ? remove

    contributions = SubSection(
        section_def=SectionProxy('PhysicalProperty'),
        repeats=True,
        description="""
        Shallow list of contributions to the physical property.
        Does not necessarily entail a (full) partioning.
        """,
    )
    # TODO: would be wishful to have `section_def` be a stripped down version of PhysicalProperty
    # that gets automatically updated when extending PhysicalProperty
    # should be discussed with @TLCFEM

    def _is_derived(self) -> bool:
        """
        Resolves whether the physical property is derived or not.

        Returns:
            (bool): The flag indicating whether the physical property is derived or not.
        """
        return self.physical_property_ref is not None

    def _is_contribution(self) -> bool:
        """
        Determines if this instance is a contribution by checking if it's contained
        in a parent's contributions list.

        Returns:
            (bool): True if this instance is a contribution, False otherwise.
        """
        if hasattr(self, 'm_parent') and self.m_parent:
            parent_section = self.m_parent
            # If parent has contributions containing this instance, we are a contribution
            if (
                hasattr(parent_section, 'contributions')
                and parent_section.contributions
            ):
                if self in parent_section.contributions:
                    return True
        return False

    @log
    def _validate_contributions_structure(self) -> bool:
        """
        Validates that contributions do not contain nested contributions.
        This prevents recursive contribution structures which are not intended.
        Only runs for top-level PhysicalProperty instances, not for contributions themselves.

        Args:
            logger: Logger instance for error reporting.

        Returns:
            (bool): True if validation passes, False if nested contributions are found.
        """
        logger = self._validate_contributions_structure.__annotations__['logger']
        # Skip validation for contribution instances
        if self._is_contribution():
            return True

        if not self.contributions:
            return True

        has_nested_contributions = False
        for i, contribution in enumerate(self.contributions):
            if hasattr(contribution, 'contributions') and contribution.contributions:
                logger.error(
                    f'Contribution {i} in {self.__class__.__name__} contains nested contributions. '
                    'Contributions should not have their own contributions subsection populated.'
                )
                has_nested_contributions = True

        return not has_nested_contributions

    def _validate_contribution_type(self, logger) -> bool:
        """
        Validates that contribution_type is only set for contribution instances
        and is not set for top-level PhysicalProperty instances.

        Args:
            logger: Logger instance for error reporting.

        Returns:
            (bool): True if validation passes, False if contribution_type is incorrectly set.
        """
        is_contribution = self._is_contribution()

        # Check for incorrect usage
        if not is_contribution and self.contribution_type is not None:
            logger.error(
                f'{self.__class__.__name__} has contribution_type set but is not a contribution. '
                'contribution_type should only be set for instances in the contributions subsection.'
            )
            return False

        return True

    def plot(self, **kwargs) -> list[PlotlyFigure]:
        """
        Placeholder for a method to plot the physical property. This method should be overridden in derived classes
        to provide specific plotting functionality.

        Returns:
            (list[PlotlyFigure]): A list of PlotlyFigure objects representing the physical property.
        """
        return []

    def sub_plots(self, **kwargs) -> None:
        """
        Collects plots from `self.contributions` and overlays them onto the target figure.
        """
        if not self.contributions or not self.figures:
            return

        try:
            target_figure = self.figures[kwargs.get('target_indices', -1)]
        except (IndexError, TypeError):
            return

        if target_figure.figure:
            figure_dict = target_figure.figure.copy()
        else:
            figure_dict = {'data': [], 'layout': {}}

        for contribution in self.contributions:
            # Use existing figures if already normalized, otherwise call plot()
            plots = (
                contribution.figures
                if contribution.figures
                else contribution.plot(**kwargs)
            )

            if plots:
                for plot in plots:
                    if hasattr(plot, 'figure') and plot.figure:
                        plot_data = plot.figure.get('data', [])
                        for trace in plot_data:
                            figure_dict['data'].append(trace)

        target_figure.figure = figure_dict

    def normalize(self, *args, **kwargs) -> None:
        # check whether already normalized
        if self.m_cache.get('_is_normalized', False):
            return
        else:
            self.m_cache['_is_normalized'] = True

        # perform own normalization
        super().normalize(*args, **kwargs)

        self.is_derived = self._is_derived()

        # validate contributions structure and contribution_type usage
        logger_arg = args[1] if len(args) > 1 else logger
        self._validate_contributions_structure(logger=logger_arg)
        self._validate_contribution_type(logger_arg)

        for contribution in self.contributions:
            if hasattr(contribution, 'normalize'):
                contribution.normalize(*args, **kwargs)

        if plot_figures := self.plot(**kwargs):
            self.figures.extend(plot_figures)
        self.sub_plots(**kwargs)

        # set names last, they may depend other normalized properties
        if self.m_def.name is not None:
            self.name = self.m_def.name
