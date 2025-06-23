from math import factorial
from typing import TYPE_CHECKING

import numpy as np
from nomad.config import config

if TYPE_CHECKING:
    from typing import Callable, Optional

    from nomad.datamodel.data import ArchiveSection
    from structlog.stdlib import BoundLogger

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


def get_sibling_section(
    section: 'ArchiveSection',
    sibling_section_name: str,
    logger: 'BoundLogger',
    index_sibling: int = 0,
) -> 'Optional[ArchiveSection]':
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


def is_not_representative(model_system, logger: 'BoundLogger'):
    """
    Checks if the given `ModelSystem` is not representative and logs a warning.

    Args:
        model_system (ModelSystem): The `ModelSystem` to check.
        logger (BoundLogger): The logger to log messages.

    Returns:
        (bool): True if the `ModelSystem` is not representative, False otherwise.
    """
    if model_system is None:
        logger.warning('The `ModelSystem` is empty.')
        return None
    if not model_system.is_representative:
        return True
    return False


# TODO remove function in nomad.atomutils
def get_composition(children_names: 'list[str]') -> str:
    """
    Generates a generalized "chemical formula" based on the provided list `children_names`,
    with the format X(m)Y(n) for children_names X and Y of quantities m and n, respectively.
    """
    children_count_tup = np.unique(children_names, return_counts=True)
    formula = ''.join([f'{name}({count})' for name, count in zip(*children_count_tup)])
    return formula if formula else None


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


def check_not_none(*attributes: str) -> 'Callable':
    """
    Decorator that checks if specified object or class attributes are not `None`.
    Returns `None` if any of the specified attributes are `None`, otherwise executes the function.

    Args:
        *attributes: Names of attributes to check for None values
            Use 'input.<attribute>' for input attributes
            Use 'self.<attribute>' for object attributes
            Use 'class.<attribute>' for class attributes
            Use '<attribute>' for global attributes
    """

    def decorator(func: 'Callable') -> 'Callable':
        import inspect
        
        def wrapper(*args, **kwargs):
            # Get function signature to map arguments by name
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            for attr in attributes:
                # Parse attribute path
                if attr.startswith('input.'):
                    param_name, attr_name = attr[6:].split('.', 1) if '.' in attr[6:] else ('', attr[6:])
                    if param_name:
                        # Specific parameter name given
                        source = bound_args.arguments.get(param_name)
                    else:
                        # Default to first parameter for backward compatibility
                        source = list(bound_args.arguments.values())[0] if bound_args.arguments else None
                elif attr.startswith('self.'):
                    attr_name = attr[5:]
                    source = bound_args.arguments.get('self')
                elif attr.startswith('class.'):
                    attr_name = attr[6:]
                    self_obj = bound_args.arguments.get('self')
                    source = self_obj.__class__ if self_obj else None
                else:
                    attr_name = attr
                    source = globals()
                
                if source is None or not hasattr(source, attr_name) or getattr(source, attr_name) is None:
                    return None

            return func(*args, **kwargs)

        return wrapper

    return decorator

def inner_copy(
    tensor: np.ndarray, rank_selection: int | tuple[int] | slice, repeat: int = 0
) -> np.ndarray:
    """
    Take a chunk of a high-ranked array and extend it with exact copies of the selection.

    This function selects a portion of a tensor along its first axis and repeats it
    the specified number of times, effectively extending the tensor.

    Args:
        tensor: Input `numpy` array to copy from
        rank_selection: `int`, `tuple`, `slice` specifying which elements to select
        repeat: Number of times to repeat the selection. Counting starts from 0 (default: 0)

    Example:
        >>> arr = np.array([[1, 2], [3, 4], [5, 6]])
        >>> inner_copy(arr, slice(0, None), repeat=2)
        array([[1, 2], [1, 2], [1, 2]])
    """
    if tensor.size == 0:
        return tensor

    selected_chunk = tensor[rank_selection]

    # If selection results in 1D array, ensure it maintains proper shape
    if selected_chunk.ndim == tensor.ndim - 1:
        selected_chunk = np.expand_dims(selected_chunk, axis=0)

    repeated_chunks = np.tile(selected_chunk, (repeat + 1, *([1] * (tensor.ndim - 1))))
    return np.concatenate([tensor, repeated_chunks], axis=0)
