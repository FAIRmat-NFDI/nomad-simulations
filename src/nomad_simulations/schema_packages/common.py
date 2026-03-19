import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import Datetime, Quantity


class SimulationTime(ArchiveSection):
    """
    Contains time-related quantities.
    """

    datetime_end = Quantity(
        type=Datetime,
        description="""
        The date and time when the computation ended.
        """,
    )

    cpu1_start = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The starting time of the computation on the (first) CPU 1.
        """,
    )

    cpu1_end = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The end time of the computation on the (first) CPU 1.
        """,
    )

    wall_start = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The internal wall-clock time from the starting of the computation.
        """,
    )

    wall_end = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The internal wall-clock time from the end of the computation.
        """,
    )
