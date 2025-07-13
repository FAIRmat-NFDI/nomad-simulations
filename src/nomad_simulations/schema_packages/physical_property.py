from nomad import utils
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.datamodel.metainfo.basesections.v2 import Entity
from nomad.metainfo import URL, MEnum, Quantity, SubSection, Reference, SectionProxy
from nomad_simulations.schema_packages.numerical_settings import SelfConsistency

from nomad.datamodel.metainfo.plot import PlotlyFigure

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
    )  # ? useful

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
        This is useful for visualizing different components of the physical property.
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

        target_indices = kwargs.get('target_indices', -1)
        target_figure = self.figures[target_indices]

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

        for contribution in self.contributions:
            if hasattr(contribution, 'normalize'):
                contribution.normalize(*args, **kwargs)

        if plot_figures := self.plot(**kwargs):
            self.figures.extend(plot_figures)
        self.sub_plots(**kwargs)

        # set names last, they may depend other normalized properties
        if self.m_def.name is not None:
            self.name = self.m_def.name
