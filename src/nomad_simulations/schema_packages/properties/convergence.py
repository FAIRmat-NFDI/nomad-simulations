from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import numpy as np

from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.numerical_settings import SelfConsistency
from nomad.metainfo import Section, Quantity, Reference


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
        type=np.dtype(np.float64),
        # guideline: specialize the unit
        shape=['*'],
        description="""
        Difference of the physical property. The shape of the value is defined by the `variables_shape` and
        the `value.shape` of the physical property.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        if not self.iteration_cycles:
            self.iteration_cycles = list(range(len(self.value)))
        if not self.diff_value:
            self.diff_value = np.diff(self.value.magnitude) * self.value.unit
