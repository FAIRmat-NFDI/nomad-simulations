import functools
import inspect
from collections import Counter
from math import factorial
from typing import TYPE_CHECKING, Any

import numpy as np
from nomad.config import config
from nomad.datamodel.data import ArchiveSection
from nomad.utils import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Optional

    from structlog.stdlib import BoundLogger

DEFAULT_LOGGER = get_logger(__name__)


def log(
    function: 'Callable' = None,
    logger: 'BoundLogger' = DEFAULT_LOGGER,
    exc_msg: str = None,
    exc_raise: bool = False,
    default: Any = None,
):
    """
    Function decorator to log exceptions.

    Args:
        function (Callable): function to evaluate
        logger (Logger, optional): logger to attach exceptions
        exc_msg (str, optional): prefix to exception
        exc_raise (bool, optional): if True will raise error
        default (Any, optional): return value of function if error
    """

    def _log(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger = kwargs.get('logger', logger)
            _exc_msg = kwargs.get(
                'exc_msg', exc_msg or f'Exception raised in {func.__name__}:'
            )
            _exc_raise = kwargs.get('exc_raise', exc_raise)
            func.__annotations__['logger'] = _logger
            try:
                return func(
                    *args,
                    **{
                        key: val
                        for key, val in kwargs.items()
                        if key in inspect.signature(func).parameters
                    },
                )
            except Exception as e:
                _logger.warning(f'{_exc_msg} {e}')
                if _exc_raise:
                    raise e
                return kwargs.get('default', default)

        return wrapper

    return _log(function) if function else _log


def get_sibling_section(
    section: 'ArchiveSection',
    sibling_section_name: str,
    logger: 'BoundLogger',
    index_sibling: int = 0,
) -> ArchiveSection | None:
    """
    Gets the sibling section of a section by performing a seesaw move by going to the parent
    of the section and then going down to the sibling section. This is used, e.g., to get
    the `AtomicCell` section from the `Symmetry` section and by passing through the `ModelSystem`.

    Example of the sections structure:

        parent_section
          |__ section
          |__ sibling_section


    If the sibling_section is a list, it returns the element `index_sibling` of that list. If
    the sibling_section is a single section, it returns the sibling_section itself.

    Args:
        section (ArchiveSection): The section to check for its parent and retrieve the sibling_section.
        sibling_section (str): The name of the sibling_section to retrieve from the parent.
        index_sibling (int): The index of the sibling_section to retrieve if it is a list.
        logger (BoundLogger): The logger to log messages.

    Returns:
        sibling_section (ArchiveSection): The sibling_section to be returned.
    """
    if not sibling_section_name:
        logger.warning('The sibling_section_name is empty.')
        return None
    sibling_section = section.m_xpath(f'm_parent.{sibling_section_name}', dict=False)
    # If the sibling_section is a list, return the element `index_sibling` of that list
    if isinstance(sibling_section, list):
        if index_sibling >= len(sibling_section):
            logger.warning('The index of the sibling_section is out of range.')
            return None
        return sibling_section[index_sibling]
    return sibling_section


# ? Check if this utils deserves its own file after extending it
class RussellSaundersState:
    @classmethod
    def generate_Js(cls, J1: float, J2: float, rising=True):
        J_min, J_max = sorted([abs(J1), abs(J2)])
        generator = range(
            int(J_max - J_min) + 1
        )  # works for both for fermions and bosons
        if rising:
            for jj in generator:
                yield J_min + jj
        else:
            for jj in generator:
                yield J_max - jj

    @classmethod
    def generate_MJs(cls, J, rising=True):
        generator = range(int(2 * J + 1))
        if rising:
            for m in generator:
                yield -J + m
        else:
            for m in generator:
                yield J - m

    def __init__(self, *args, **kwargs):
        self.J = kwargs.get('J')
        if self.J is None:
            raise TypeError
        self.occupation = kwargs.get('occ')
        if self.occupation is None:
            raise TypeError

    @property
    def multiplicity(self):
        return 2 * self.J + 1

    @property
    def degeneracy(self):
        return factorial(int(self.multiplicity)) / (
            factorial(int(self.multiplicity - self.occupation))
            * factorial(self.occupation)
        )


# TODO remove function in nomad.atomutils
def get_composition(children_names: list[str]) -> str | None:
    """
    Build a canonical composition string like ``X(m)Y(n)`` from child names.

    Notes
    -----
    - Names are **counted case-sensitively** (``"A"`` and ``"a"`` are distinct).
    - Output terms are ordered by a **case-insensitive** primary sort
      (using ``str.casefold()``), with a **deterministic tie-breaker** on the
      original string (i.e., sorted by ``(name.casefold(), name)``).
      This makes the result independent of the input order while preserving
      distinct case variants as separate terms.
    - All items are converted to strings via ``str(...)`` before counting.
    - Returns ``None`` if the input list is empty.

    Parameters
    ----------
    children_names : list[str]
        Child names to count.

    Returns
    -------
    str | None
        Canonical composition string, or ``None`` if no names were provided.

    Examples
    --------
    >>> get_composition(['H', 'O', 'H'])
    'H(2)O(1)'
    >>> get_composition(['a', 'A', 'b'])
    'A(1)a(1)b(1)'
    """
    if not children_names:
        return None

    counts = Counter(map(str, children_names))
    parts = [
        f'{name}({counts[name]})'
        for name in sorted(counts, key=lambda s: (s.casefold(), s))
    ]
    return ''.join(parts) if parts else None


def catch_not_implemented(func: 'Callable') -> 'Callable':
    """
    Decorator to default comparison functions outside the same class to `False`.
    """

    def wrapper(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False  # ? should this throw an error instead?
        try:
            return func(self, other)
        except (TypeError, NotImplementedError):
            return False

    return wrapper
