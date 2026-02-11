# scripts/meta_introspect.py
from __future__ import annotations
import importlib
import inspect
import pkgutil
import sys
from typing import Any, Iterable, Optional, get_args, get_origin

from nomad.metainfo import MSection


# ------------------------- discovery -------------------------


def ensure_nomad_datamodel_compat() -> None:
    """
    Backfill symbols removed from newer ``nomad.datamodel`` releases.

    The schema package still imports several metainfo symbols from
    ``nomad.datamodel``. Newer NOMAD versions moved these under
    ``nomad.metainfo``. This shim keeps introspection scripts working
    without requiring mass refactors across schema files.
    """
    try:
        datamodel = importlib.import_module('nomad.datamodel')
        metainfo = importlib.import_module('nomad.metainfo')
    except Exception:
        return

    moved_symbols = (
        'Datetime',
        'JSON',
        'MEnum',
        'Quantity',
        'Reference',
        'SchemaPackage',
        'Section',
        'SectionProxy',
        'SubSection',
        'URL',
    )
    for symbol in moved_symbols:
        if hasattr(datamodel, symbol):
            continue
        try:
            setattr(datamodel, symbol, getattr(metainfo, symbol))
        except Exception:
            continue

    # Older code imports nomad.datamodel.data_type, now in nomad.metainfo.data_type
    if 'nomad.datamodel.data_type' not in sys.modules:
        try:
            data_type_mod = importlib.import_module('nomad.metainfo.data_type')
            sys.modules['nomad.datamodel.data_type'] = data_type_mod
        except Exception:
            pass


def _iter_modules_recursively(root_module):
    """Yield the root module + all submodules under its package."""
    yield root_module
    if not hasattr(root_module, '__path__'):
        return
    for modinfo in pkgutil.walk_packages(
        root_module.__path__, root_module.__name__ + '.'
    ):
        try:
            yield importlib.import_module(modinfo.name)
        except Exception:
            # Keep introspection resilient even if some submodule imports fail
            continue


def issubclass_safe(obj: Any, base: type) -> bool:
    try:
        return inspect.isclass(obj) and issubclass(obj, base)
    except Exception:
        return False


def iter_section_classes(pkg: str) -> Iterable[type[MSection]]:
    """
    Yield all MSection subclasses defined under a package (recursively).
    Only returns concrete subclasses (excludes MSection itself).
    """
    ensure_nomad_datamodel_compat()
    root = importlib.import_module(pkg)
    for m in _iter_modules_recursively(root):
        for _, obj in inspect.getmembers(m, inspect.isclass):
            if obj is MSection:
                continue
            if issubclass_safe(obj, MSection):
                yield obj


# ------------------------- typing helpers -------------------------


def _flatten_types(t: Any) -> Iterable[Any]:
    """
    Recursively unwrap typing constructs:
      - Optional[T], Union[T1, T2], list[T], dict[K, V], tuple[T,...], Annotated[T, ...]
    Returns a flat iterable of underlying argument types (including T).
    """
    origin = get_origin(t)
    if origin is None:
        yield t
        return

    # typing.Annotated[T, ...] -> just T
    if str(origin).endswith('Annotated'):
        args = get_args(t)
        if args:
            yield from _flatten_types(args[0])
        return

    for arg in get_args(t):
        yield from _flatten_types(arg)


def _as_section_cls(candidate: Any) -> type[MSection] | None:
    """
    Interpret a candidate as an MSection class if possible.
    Handles:
      - Direct MSection subclass
      - NOMAD reference wrappers exposing .section_def / .target_section_def / .section_cls
      - Instances exposing .m_def.section_cls
    """
    # Direct class
    if issubclass_safe(candidate, MSection):
        return candidate

    # Reference-like wrappers often expose these
    for attr in ('section_def', 'target_section_def', 'section_cls'):
        sec = getattr(candidate, attr, None)
        if issubclass_safe(sec, MSection):
            return sec

    # Instances with m_def
    mdef = getattr(candidate, 'm_def', None)
    sec_cls = getattr(mdef, 'section_cls', None) if mdef is not None else None
    if issubclass_safe(sec_cls, MSection):
        return sec_cls

    return None


# ------------------------- metainfo container helpers -------------------------


def _iter_defs(container: Any):
    """
    Yield definition items from NOMAD metainfo containers:
    works for MSubSectionList/MQuantityList (iterables) and plain dicts.
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


def _get_child_section_cls(ss_def: Any):
    """
    Try common attributes to get the child MSection class from a SubSection def.
    """
    # Typical attributes
    for attr in ('sub_section', 'section_def', 'section_cls'):
        cls = getattr(ss_def, attr, None)
        if issubclass_safe(cls, MSection):
            return cls
    # Occasionally nested: .sub_section.section_cls
    sub = getattr(ss_def, 'sub_section', None)
    cls = getattr(sub, 'section_cls', None)
    if issubclass_safe(cls, MSection):
        return cls
    return None


# ------------------------- edge extraction -------------------------


def section_edges(section_cls: type[MSection]) -> dict[str, list[tuple[str, str, str]]]:
    """
    Return edges for a single section:
      contain: parent --> child (from SubSection)
      refs:    source ..> target (from Quantity types referencing sections)
      inherit: child <|-- parent (inheritance relationship)
    Each edge is a tuple (source_name, target_name, label).
    """
    sdef = section_cls.m_def

    contain: set[tuple[str, str, str]] = set()
    for ss in _iter_defs(getattr(sdef, 'sub_sections', None)):
        child_cls = _get_child_section_cls(ss)
        if child_cls is not None:
            label = getattr(ss, 'name', getattr(ss, 'path', 'subsection'))
            contain.add((section_cls.__name__, child_cls.__name__, label))

    refs: set[tuple[str, str, str]] = set()
    for q in _iter_defs(getattr(sdef, 'quantities', None)):
        qtype = getattr(q, 'type', None)
        if qtype is None:
            continue
        for t in _flatten_types(qtype):
            sec_cls = _as_section_cls(t)
            if sec_cls is not None:
                label = getattr(q, 'name', 'ref')
                refs.add((section_cls.__name__, sec_cls.__name__, label))

    # Collect inheritance edges
    inherit: set[tuple[str, str, str]] = set()
    for base in section_cls.__bases__:
        if issubclass_safe(base, MSection) and base is not MSection:
            # Inheritance: child <|-- parent
            inherit.add((section_cls.__name__, base.__name__, ''))

    return {'contain': sorted(contain), 'refs': sorted(refs), 'inherit': sorted(inherit)}


# ------------------------- aggregate across package -------------------------


def _include_edge(
    edge: tuple[str, str, str], module_by_name: dict[str, str], prefix: Optional[str]
) -> bool:
    if not prefix:
        return True
    a, b, _ = edge
    ma = module_by_name.get(a, '')
    mb = module_by_name.get(b, '')
    return ma.startswith(prefix) and mb.startswith(prefix)


def collect_edges(
    pkg: str, only_modules_prefix: Optional[str] = None
) -> dict[str, list[tuple[str, str, str]]]:
    """
    Aggregate 'contain', 'refs', and 'inherit' edges across all MSection classes found
    under the given package. Optionally restrict edges to those whose endpoint
    classes live under 'only_modules_prefix' (to avoid pulling in big externals).
    """
    contain_all: set[tuple[str, str, str]] = set()
    refs_all: set[tuple[str, str, str]] = set()
    inherit_all: set[tuple[str, str, str]] = set()

    classes = list(iter_section_classes(pkg))
    module_by_name = {cls.__name__: cls.__module__ for cls in classes}

    for cls in classes:
        edges = section_edges(cls)
        for e in edges['contain']:
            if _include_edge(e, module_by_name, only_modules_prefix):
                contain_all.add(e)
        for e in edges['refs']:
            if _include_edge(e, module_by_name, only_modules_prefix):
                refs_all.add(e)
        for e in edges['inherit']:
            if _include_edge(e, module_by_name, only_modules_prefix):
                inherit_all.add(e)

    return {
        'contain': sorted(contain_all),
        'refs': sorted(refs_all),
        'inherit': sorted(inherit_all),
    }


__all__ = [
    'iter_section_classes',
    'section_edges',
    'collect_edges',
]
