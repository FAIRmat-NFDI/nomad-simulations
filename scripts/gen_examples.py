# scripts/gen_examples.py
from __future__ import annotations

import inspect
from typing import Any, get_args, get_origin

from nomad.metainfo import MSection

# ----------------- helpers -----------------


def _iter_defs(container: Any):
    """
    Iterate over NOMAD metainfo containers:
    works for MQuantityList/MSubSectionList (iterables) and dicts.
    """
    if container is None:
        return
    if isinstance(container, dict):
        for v in container.values():
            yield v
        return
    try:
        for v in container:
            yield v
    except TypeError:
        return


def _is_section_type(t: Any) -> bool:
    """
    Check if a type represents (or wraps) an MSection subclass.
    Handles typing wrappers and reference-like wrappers with .section_def/.section_cls.
    """
    if inspect.isclass(t) and issubclass(t, MSection):
        return True
    for attr in ('section_def', 'target_section_def', 'section_cls'):
        sec = getattr(t, attr, None)
        if inspect.isclass(sec) and issubclass(sec, MSection):
            return True
    return False


def _unwrap_type(t: Any):
    """
    Yield underlying types from typing constructs:
    Optional[T], Union, list[T], Annotated[T, ...], etc.
    """
    origin = get_origin(t)
    if origin is None:
        yield t
        return
    # typing.Annotated[T, ...] -> T
    if str(origin).endswith('Annotated'):
        args = get_args(t)
        if args:
            yield from _unwrap_type(args[0])
        return
    for arg in get_args(t):
        yield from _unwrap_type(arg)


def _placeholder_for_quantity(q) -> Any:
    """
    Produce a small, shape/unit-aware placeholder for a Quantity.
    - If default is present, use it.
    - If it references a section, return None (or a tiny ref stub).
    - Otherwise choose a scalar placeholder by dtype.
    """
    # Default beats everything
    if getattr(q, 'default', None) is not None:
        return q.default

    # Section references: leave as None (could be replaced by {"$ref": "<Section>"} if desired)
    qtype = getattr(q, 'type', None)
    if qtype is not None:
        for t in _unwrap_type(qtype):
            if _is_section_type(t):
                return None

    # Primitive placeholders by dtype name (best-effort)
    dtype = getattr(q, 'dtype', None)
    shape = getattr(q, 'shape', None)

    base = None
    if dtype is None:
        base = None
    else:
        # dtype names in NOMAD often look like 'np.float64', 'np.int64', 'str', 'bool'
        name = str(dtype)
        if 'float' in name:
            base = 0.0
        elif 'int' in name:
            base = 0
        elif 'bool' in name:
            base = False
        elif 'str' in name:
            base = ''
        else:
            base = None

    # If shape indicates an array, wrap placeholder accordingly
    # Common patterns: (), (3,), (n_atoms, 3), None, or string expressions
    if shape in (None, '', (), '()', 1):
        value = base
    else:
        # Make a tiny shape-aware stub without trying to compute symbolic dims
        value = [base]

    # If unit exists and value is numeric, you can keep it numeric; docs can show unit separately.
    # If you prefer an annotated string like "0.0 eV", uncomment:
    # if unit is not None and isinstance(value, (int, float)):
    #     value = f"{value} {unit}"

    return value


def _child_section_cls(ss_def: Any):
    """
    Try to obtain the child MSection class from a SubSection def.
    """
    for attr in ('sub_section', 'section_def', 'section_cls'):
        cls = getattr(ss_def, attr, None)
        if inspect.isclass(cls) and issubclass(cls, MSection):
            return cls
    sub = getattr(ss_def, 'sub_section', None)
    cls = getattr(sub, 'section_cls', None)
    if inspect.isclass(cls) and issubclass(cls, MSection):
        return cls
    return None


# ----------------- main API -----------------


def example_for_section(section_cls: type[MSection], depth: int = 1) -> dict:
    """
    Build a minimal example mapping for a given MSection subclass:
      - includes all quantities with sensible placeholders/defaults
      - includes one level of subsections (empty object or single empty item for repeats)
    Returns a Python dict (the caller can YAML-dump it).
    """
    if not inspect.isclass(section_cls) or not issubclass(section_cls, MSection):
        raise TypeError('example_for_section expects an MSection subclass')

    sdef = section_cls.m_def
    data: dict[str, Any] = {}

    # Quantities
    for q in _iter_defs(getattr(sdef, 'quantities', None)):
        name = getattr(q, 'name', 'quantity')
        data[name] = _placeholder_for_quantity(q)

    # One level of subsections
    if depth > 0:
        for ss in _iter_defs(getattr(sdef, 'sub_sections', None)):
            child_cls = _child_section_cls(ss)
            if child_cls is None:
                continue
            ss_name = getattr(ss, 'name', 'subsection')
            if getattr(ss, 'repeats', False):
                # For repeats, provide a single minimal child object (empty) to show the shape
                data[ss_name] = [{}]
            else:
                data[ss_name] = {}

    return data
