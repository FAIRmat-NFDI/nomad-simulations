from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import numpy as np
from nomad.metainfo import Quantity, Reference, Section

from nomad_simulations.schema_packages.numerical_settings import SelfConsistency
from nomad_simulations.schema_packages.physical_property import PhysicalProperty


class ConvergenceMetric(PhysicalProperty):
    """
    Abstract physical property section linking a property contribution to a convergence
    from some method.

    Abstract class for incorporating specific convergence of a physical property, while
    linking this convergence to a specific component (of class `BaseModelMethod`) of the
    over `ModelMethod` using the `model_method_ref` quantity.
    """

    m_def = Section(
        a_plotly_express=[
            {
                'label': 'convergence',
                'x': '#iteration_cycles',
                'y': '#value',
                'mode': 'lines',
                'secondary_y': False,
            },
            {
                'label': 'convergence',
                'x': '#iteration_cycles',
                'y': '#diff_value',
                'mode': 'scatter',
                'secondary_y': True,
            },
        ],
        a_plotly_graph_object={
            'type': 'line',
            'x0': 0,
            'x1': '#settings.n_max_iterations',
            'y0': '#settings.differential_threshold',
            'y1': '#settings.differential_threshold',
        },
    )

    settings = Quantity(
        type=Reference(SelfConsistency),
        description="""
        Reference to the `SelfConsistency` section to which the convergence is linked to.
        """,
    )

    iteration_cycles = Quantity(
        type=int,
        shape=['*'],
        description="""
        Number of iteration cycles performed to reach the convergence.
        """,
    )  # ? Could this be set dynamically

    value = Quantity(
        type=np.dtype(np.float64),
        # guideline: specialize the unit
        shape=['*'],
        description="""
        Value of the physical property. The shape of the value is defined by the `variables_shape` and
        the `value.shape` of the physical property.
        """,
    )

    diff_value = Quantity(
        type=np.dtype(np.float64),  # ? absolute value
        # guideline: specialize the unit
        shape=['*'],
        description="""
        Difference of the physical property. The shape of the value is defined by the `variables_shape` and
        the `value.shape` of the physical property.
        """,
    )

    is_scf_converged = Quantity(
        type=bool,
        description="""
        Boolean value indicating whether the convergence is reached or not, according to the `settings`.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalize the convergence metric by setting the iteration cycles and diff_value.
        `settings` should receive its data via `after_normalize`.
        """  # ? is `after_normalize` appropriate here
        super().normalize(archive, logger)
        if not self.iteration_cycles:
            self.iteration_cycles = list(range(len(self.value)))
        if not self.diff_value:
            self.diff_value = np.abs(np.diff(self.value.magnitude)) * self.value.unit
        if not self.is_scf_converged:
            self.is_scf_converged = np.all(
                self.diff_value < self.settings.differential_threshold
            )


class EnergyConvergence(ConvergenceMetric):
    # TODO: generate enum for `name`

    value = ConvergenceMetric.m_def.value.m_copy()
    value.unit = 'J'

    diff_value = ConvergenceMetric.m_def.diff_value.m_copy()
    diff_value.unit = 'J'


class ForceConvergence(ConvergenceMetric):
    value = ConvergenceMetric.m_def.value.m_copy()
    value.unit = 'N'

    diff_value = ConvergenceMetric.m_def.diff_value.m_copy()
    diff_value.unit = 'N'
