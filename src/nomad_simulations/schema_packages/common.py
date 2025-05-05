import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.annotations import ELNAnnotation
from nomad.metainfo import Datetime, Quantity


class Time(ArchiveSection):
    """
    Contains time-related quantities.
    """

    datetime_end = Quantity(
        type=Datetime,
        description="""
        The date and time when this computation ended.
        """,
        a_eln=ELNAnnotation(component='DateTimeEditQuantity'),
    )

    cpu1_start = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The starting time of the computation on the (first) CPU 1.
        """,
        a_eln=ELNAnnotation(component='NumberEditQuantity'),
    )

    cpu1_end = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The end time of the computation on the (first) CPU 1.
        """,
        a_eln=ELNAnnotation(component='NumberEditQuantity'),
    )

    wall_start = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The internal wall-clock time from the starting of the computation.
        """,
        a_eln=ELNAnnotation(component='NumberEditQuantity'),
    )

    wall_end = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The internal wall-clock time from the end of the computation.
        """,
        a_eln=ELNAnnotation(component='NumberEditQuantity'),
    )
