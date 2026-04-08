from __future__ import annotations

import ast
import importlib
import inspect
import json
import pkgutil
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args, get_origin
from urllib.parse import quote

DEFAULT_SCHEMA_PACKAGE = 'nomad_simulations.schema_packages'
DEFAULT_BASE_URI = 'https://fairmat-nfdi.github.io/nomad-simulations/rdf/'
VOCAB_URI = 'https://fairmat-nfdi.github.io/nomad-simulations/vocab/'

RDF_NS = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
RDFS_NS = 'http://www.w3.org/2000/01/rdf-schema#'
OWL_NS = 'http://www.w3.org/2002/07/owl#'
XSD_NS = 'http://www.w3.org/2001/XMLSchema#'

PREFIXES: tuple[tuple[str, str], ...] = (
    ('rdf', RDF_NS),
    ('rdfs', RDFS_NS),
    ('owl', OWL_NS),
    ('xsd', XSD_NS),
    ('nomad', VOCAB_URI),
)


@dataclass(frozen=True, order=True)
class RDFNode:
    value: str
    is_literal: bool = False
    datatype: str | None = None


@dataclass(frozen=True, order=True)
class RDFTriple:
    subject: str
    predicate: str
    object: RDFNode


@dataclass(frozen=True)
class SourceQuantity:
    name: str
    type_expr: str | None = None
    description: str | None = None
    shape: str | None = None
    unit: str | None = None
    enum_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceSubSection:
    name: str
    target_name: str | None = None
    description: str | None = None
    repeats: bool = False


@dataclass(frozen=True)
class SourceSection:
    name: str
    module: str
    description: str | None = None
    links: tuple[str, ...] = ()
    base_names: tuple[str, ...] = ()
    quantities: tuple[SourceQuantity, ...] = ()
    sub_sections: tuple[SourceSubSection, ...] = ()


def _resource(value: str) -> RDFNode:
    return RDFNode(value=value, is_literal=False)


def _literal(value: str, datatype: str | None = None) -> RDFNode:
    return RDFNode(value=value, is_literal=True, datatype=datatype)


def _join_iri(base_uri: str, suffix: str) -> str:
    base = base_uri if base_uri.endswith(('#', '/')) else f'{base_uri}/'
    return f'{base}{suffix}'


def _safe_local_name(value: str) -> bool:
    if not value:
        return False
    if not (value[0].isalpha() or value[0] == '_'):
        return False
    return all(char.isalnum() or char in '._-' for char in value)


def _format_iri(value: str, extra_prefixes: Iterable[tuple[str, str]] = ()) -> str:
    for prefix, namespace in (*PREFIXES, *tuple(extra_prefixes)):
        if value.startswith(namespace):
            local = value[len(namespace) :]
            if _safe_local_name(local):
                return f'{prefix}:{local}'
    return f'<{value}>'


def _escape_literal(value: str) -> str:
    return (
        value.replace('\\', '\\\\')
        .replace('"', '\\"')
        .replace('\n', '\\n')
        .replace('\r', '\\r')
        .replace('\t', '\\t')
    )


def _format_node(node: RDFNode, extra_prefixes: Iterable[tuple[str, str]] = ()) -> str:
    if not node.is_literal:
        return _format_iri(node.value, extra_prefixes=extra_prefixes)

    literal = f'"{_escape_literal(node.value)}"'
    if node.datatype:
        return f'{literal}^^{_format_iri(node.datatype, extra_prefixes=extra_prefixes)}'
    return literal


def serialize_turtle(
    triples: Iterable[RDFTriple], base_uri: str = DEFAULT_BASE_URI
) -> str:
    """
    Serialize RDF triples as deterministic Turtle.
    """
    base = base_uri if base_uri.endswith(('#', '/')) else f'{base_uri}/'
    lines = [f'@prefix ns: <{base}> .']
    lines.extend(f'@prefix {prefix}: <{namespace}> .' for prefix, namespace in PREFIXES)
    lines.append('')

    for triple in sorted(set(triples)):
        subject = _format_iri(triple.subject, extra_prefixes=(('ns', base),))
        predicate = _format_iri(triple.predicate, extra_prefixes=(('ns', base),))
        obj = _format_node(triple.object, extra_prefixes=(('ns', base),))
        lines.append(f'{subject} {predicate} {obj} .')

    lines.append('')
    return '\n'.join(lines)


def ensure_nomad_datamodel_compat() -> None:
    """
    Backfill symbols moved from ``nomad.datamodel`` to ``nomad.metainfo``.
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

    if 'nomad.datamodel.data_type' not in sys.modules:
        try:
            data_type_mod = importlib.import_module('nomad.metainfo.data_type')
        except Exception:
            return
        sys.modules['nomad.datamodel.data_type'] = data_type_mod


def _iter_modules_recursively(root_module) -> Iterator[Any]:
    yield root_module
    if not hasattr(root_module, '__path__'):
        return
    for modinfo in pkgutil.walk_packages(root_module.__path__, root_module.__name__ + '.'):
        try:
            yield importlib.import_module(modinfo.name)
        except Exception:
            continue


def _issubclass_safe(obj: Any, base: type) -> bool:
    try:
        return inspect.isclass(obj) and issubclass(obj, base)
    except Exception:
        return False


def discover_schema_section_classes(
    package: str = DEFAULT_SCHEMA_PACKAGE,
) -> list[type]:
    """
    Discover all NOMAD metainfo section classes below the given package.
    """
    ensure_nomad_datamodel_compat()
    try:
        from nomad.metainfo import MSection
    except Exception as exc:
        raise RuntimeError(
            'Could not import nomad.metainfo.MSection. '
            'Install the NOMAD dependencies before exporting RDF.'
        ) from exc

    root = importlib.import_module(package)
    section_classes: list[type] = []
    for module in _iter_modules_recursively(root):
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is MSection:
                continue
            if _issubclass_safe(obj, MSection):
                section_classes.append(obj)

    return sorted(
        set(section_classes), key=lambda section_cls: _qualified_class_name(section_cls)
    )


def _iter_defs(container: Any) -> Iterator[Any]:
    if container is None:
        return
    if isinstance(container, dict):
        yield from container.values()
        return
    try:
        yield from container
    except TypeError:
        return


def _flatten_types(type_hint: Any) -> Iterator[Any]:
    origin = get_origin(type_hint)
    if origin is None:
        yield type_hint
        return

    if str(origin).endswith('Annotated'):
        args = get_args(type_hint)
        if args:
            yield from _flatten_types(args[0])
        return

    for arg in get_args(type_hint):
        yield from _flatten_types(arg)


def _resolved(value: Any) -> Any:
    try:
        return value.m_resolved()
    except Exception:
        return value


def _as_section_cls(candidate: Any) -> type | None:
    candidate = _resolved(candidate)

    if inspect.isclass(candidate) and hasattr(candidate, 'm_def'):
        return candidate

    for attr in ('section_def', 'target_section_def', 'section_cls'):
        section_like = _resolved(getattr(candidate, attr, None))
        if inspect.isclass(section_like) and hasattr(section_like, 'm_def'):
            return section_like
        section_cls = getattr(section_like, 'section_cls', None)
        if inspect.isclass(section_cls) and hasattr(section_cls, 'm_def'):
            return section_cls

    m_def = _resolved(getattr(candidate, 'm_def', None))
    section_cls = getattr(m_def, 'section_cls', None)
    if inspect.isclass(section_cls) and hasattr(section_cls, 'm_def'):
        return section_cls

    return None


def _qualified_class_name(section_cls: type) -> str:
    return f'{section_cls.__module__}.{section_cls.__name__}'


def _qualified_source_name(section: SourceSection) -> str:
    return f'{section.module}.{section.name}'


def _section_uri(section_cls: type, base_uri: str) -> str:
    return _join_iri(
        base_uri, f'section/{quote(_qualified_class_name(section_cls), safe="")}'
    )


def _property_uri(
    section_cls: type, property_name: str, base_uri: str, kind: str
) -> str:
    qualified_name = quote(_qualified_class_name(section_cls), safe='')
    encoded_name = quote(property_name, safe='')
    return _join_iri(base_uri, f'{kind}/{qualified_name}/{encoded_name}')


def _type_name(type_hint: Any) -> str:
    resolved = _resolved(type_hint)
    if resolved is Any:
        return 'Any'

    if hasattr(resolved, '__name__'):
        return resolved.__name__

    resolved_class = getattr(resolved, '__class__', None)
    if resolved_class is not None and hasattr(resolved_class, '__name__'):
        return resolved_class.__name__

    return str(resolved)


def _datatype_uri(type_hint: Any, base_uri: str) -> str:
    return _join_iri(base_uri, f'datatype/{quote(_type_name(type_hint), safe="")}')


def _datatype_uri_from_name(type_name: str, base_uri: str) -> str:
    return _join_iri(base_uri, f'datatype/{quote(type_name, safe="")}')


def _description_for(item: Any) -> str | None:
    description = getattr(item, 'description', None)
    if isinstance(description, str):
        description = description.strip()
        if description:
            return description

    docstring = getattr(item, '__doc__', None)
    if isinstance(docstring, str):
        docstring = inspect.cleandoc(docstring).strip()
        if docstring:
            return docstring

    return None


def _iter_links(section_def: Any) -> Iterator[str]:
    links = getattr(section_def, 'links', None)
    if not links:
        return
    for link in links:
        if isinstance(link, str) and link:
            yield link


def _default_source_root(package: str) -> Path:
    if package != DEFAULT_SCHEMA_PACKAGE:
        raise RuntimeError(
            f'Source fallback currently supports {DEFAULT_SCHEMA_PACKAGE!r} only.'
        )
    return Path(__file__).resolve().parent / 'schema_packages'


def _ast_to_source(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _extract_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_string_list(node: ast.AST | None) -> tuple[str, ...]:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return ()
    values: list[str] = []
    for item in node.elts:
        value = _extract_string(item)
        if value is not None:
            values.append(value)
    return tuple(values)


def _extract_bool(node: ast.AST | None, default: bool = False) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return default


def _call_keyword(call: ast.Call, keyword_name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == keyword_name:
            return keyword.value
    return None


def _call_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _extract_target_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute):
        if node.attr == 'm_def':
            return _extract_target_name(node.value)
        return node.attr
    if isinstance(node, ast.Call):
        func_name = _call_name(node.func)
        if func_name in {'Reference', 'SectionProxy'} and node.args:
            return _extract_target_name(node.args[0])
    return None


def _extract_enum_values(node: ast.AST | None) -> tuple[str, ...]:
    if not isinstance(node, ast.Call) or _call_name(node.func) != 'MEnum':
        return ()
    values: list[str] = []
    for arg in node.args:
        value = _extract_string(arg)
        if value is not None:
            values.append(value)
    return tuple(values)


def _is_call(node: ast.AST | None, name: str) -> bool:
    return isinstance(node, ast.Call) and _call_name(node.func) == name


def _module_name_from_path(root: Path, path: Path, package: str) -> str:
    relative = path.relative_to(root)
    parts = list(relative.parts)
    if parts[-1] == '__init__.py':
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]
    return '.'.join([package, *parts]) if parts else package


def _parse_source_section(
    class_node: ast.ClassDef,
    module_name: str,
) -> SourceSection:
    description = ast.get_docstring(class_node)
    links: tuple[str, ...] = ()
    quantities: list[SourceQuantity] = []
    sub_sections: list[SourceSubSection] = []
    base_names = tuple(
        base_name
        for base in class_node.bases
        if (base_name := _extract_target_name(base)) is not None
    )

    for statement in class_node.body:
        target_name: str | None = None
        value: ast.AST | None = None

        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target = statement.targets[0]
            if isinstance(target, ast.Name):
                target_name = target.id
                value = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            target_name = statement.target.id
            value = statement.value

        if target_name is None or value is None or not isinstance(value, ast.Call):
            continue

        if target_name == 'm_def' and _is_call(value, 'Section'):
            links = _extract_string_list(_call_keyword(value, 'links'))
            continue

        if _is_call(value, 'Quantity'):
            quantities.append(
                SourceQuantity(
                    name=target_name,
                    type_expr=_ast_to_source(_call_keyword(value, 'type')),
                    description=_extract_string(_call_keyword(value, 'description')),
                    shape=_ast_to_source(_call_keyword(value, 'shape')),
                    unit=_ast_to_source(_call_keyword(value, 'unit')),
                    enum_values=_extract_enum_values(_call_keyword(value, 'type')),
                )
            )
            continue

        if _is_call(value, 'SubSection'):
            sub_sections.append(
                SourceSubSection(
                    name=target_name,
                    target_name=_extract_target_name(_call_keyword(value, 'sub_section')),
                    description=_extract_string(_call_keyword(value, 'description')),
                    repeats=_extract_bool(_call_keyword(value, 'repeats')),
                )
            )

    return SourceSection(
        name=class_node.name,
        module=module_name,
        description=description.strip() if description else None,
        links=links,
        base_names=base_names,
        quantities=tuple(quantities),
        sub_sections=tuple(sub_sections),
    )


def _iter_source_sections(package: str) -> Iterator[SourceSection]:
    root = _default_source_root(package)
    for path in sorted(root.rglob('*.py')):
        module_name = _module_name_from_path(root, path, package)
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                yield _parse_source_section(node, module_name)


def _source_section_uri(section: SourceSection, base_uri: str) -> str:
    return _join_iri(
        base_uri, f'section/{quote(_qualified_source_name(section), safe="")}'
    )


def _source_property_uri(
    section: SourceSection, property_name: str, base_uri: str, kind: str
) -> str:
    qualified_name = quote(_qualified_source_name(section), safe='')
    return _join_iri(base_uri, f'{kind}/{qualified_name}/{quote(property_name, safe="")}')


def _normalize_type_name(type_expr: str | None) -> str | None:
    if not type_expr:
        return None
    compact = type_expr.replace(' ', '')
    if compact.startswith('Reference(') and compact.endswith(')'):
        inner = compact[len('Reference(') : -1]
        return _normalize_type_name(inner)
    if compact.startswith('Optional[') and compact.endswith(']'):
        inner = compact[len('Optional[') : -1]
        return _normalize_type_name(inner)
    if compact.startswith('SectionProxy(') and compact.endswith(')'):
        inner = compact[len('SectionProxy(') : -1].strip("'\"")
        return inner
    if compact.endswith('.m_def'):
        compact = compact[:-6]
    if '.' in compact:
        compact = compact.split('.')[-1]
    return compact.strip("'\"")


def _source_range_resource(
    type_expr: str | None,
    enum_values: tuple[str, ...],
    section_by_name: dict[str, SourceSection],
    base_uri: str,
) -> tuple[str | None, list[RDFTriple]]:
    type_name = _normalize_type_name(type_expr)
    if not type_name:
        return f'{RDFS_NS}Literal', []

    if type_name in section_by_name:
        return _source_section_uri(section_by_name[type_name], base_uri), []

    if enum_values:
        return f'{XSD_NS}string', []
    if type_name in {'str', 'm_str', 'URL'}:
        return f'{XSD_NS}string', []
    if type_name in {'bool'}:
        return f'{XSD_NS}boolean', []
    if type_name in {
        'int',
        'np.int32',
        'np.int64',
        'np.uint32',
        'np.uint64',
        'int32',
        'int64',
        'uint32',
        'uint64',
    }:
        return f'{XSD_NS}integer', []
    if type_name in {'float', 'np.float32', 'np.float64', 'float32', 'float64'}:
        return f'{XSD_NS}double', []
    if type_name in {'Datetime', 'datetime'}:
        return f'{XSD_NS}dateTime', []
    if type_name in {'Any', 'JSON'}:
        return f'{RDFS_NS}Literal', []

    datatype_uri = _datatype_uri_from_name(type_name, base_uri)
    datatype_triples = [
        RDFTriple(datatype_uri, f'{RDF_NS}type', _resource(f'{RDFS_NS}Datatype')),
        RDFTriple(datatype_uri, f'{RDFS_NS}label', _literal(type_name)),
    ]
    return datatype_uri, datatype_triples


def source_package_to_rdf_triples(
    package: str = DEFAULT_SCHEMA_PACKAGE, base_uri: str = DEFAULT_BASE_URI
) -> list[RDFTriple]:
    sections = list(_iter_source_sections(package))
    section_by_name = {
        section.name: section
        for section in sections
        if sum(other.name == section.name for other in sections) == 1
    }

    triples: list[RDFTriple] = _vocab_triples()
    for section in sections:
        section_uri = _source_section_uri(section, base_uri)
        qualified_name = _qualified_source_name(section)
        triples.extend(
            [
                RDFTriple(section_uri, f'{RDF_NS}type', _resource(f'{OWL_NS}Class')),
                RDFTriple(section_uri, f'{RDFS_NS}label', _literal(section.name)),
                RDFTriple(section_uri, f'{VOCAB_URI}pythonModule', _literal(section.module)),
                RDFTriple(section_uri, f'{VOCAB_URI}pythonClass', _literal(qualified_name)),
            ]
        )
        if section.description:
            triples.append(
                RDFTriple(section_uri, f'{RDFS_NS}comment', _literal(section.description))
            )
        for link in section.links:
            triples.append(RDFTriple(section_uri, f'{RDFS_NS}seeAlso', _resource(link)))

        for base_name in section.base_names:
            base_section = section_by_name.get(base_name)
            if base_section is None:
                continue
            triples.append(
                RDFTriple(
                    section_uri,
                    f'{RDFS_NS}subClassOf',
                    _resource(_source_section_uri(base_section, base_uri)),
                )
            )

        for quantity in section.quantities:
            property_uri = _source_property_uri(
                section, quantity.name, base_uri, kind='quantity'
            )
            triples.append(
                RDFTriple(section_uri, f'{VOCAB_URI}definesProperty', _resource(property_uri))
            )
            range_uri, range_triples = _source_range_resource(
                quantity.type_expr,
                quantity.enum_values,
                section_by_name,
                base_uri,
            )
            triples.extend(range_triples)
            property_type = (
                f'{OWL_NS}ObjectProperty'
                if range_uri and range_uri.startswith(_join_iri(base_uri, 'section/'))
                else f'{OWL_NS}DatatypeProperty'
            )
            triples.extend(
                [
                    RDFTriple(property_uri, f'{RDF_NS}type', _resource(property_type)),
                    RDFTriple(property_uri, f'{RDFS_NS}label', _literal(quantity.name)),
                    RDFTriple(property_uri, f'{RDFS_NS}domain', _resource(section_uri)),
                    RDFTriple(property_uri, f'{VOCAB_URI}propertyKind', _literal('quantity')),
                ]
            )
            if range_uri:
                triples.append(
                    RDFTriple(property_uri, f'{RDFS_NS}range', _resource(range_uri))
                )
            if quantity.description:
                triples.append(
                    RDFTriple(property_uri, f'{RDFS_NS}comment', _literal(quantity.description))
                )
            if quantity.shape:
                triples.append(
                    RDFTriple(
                        property_uri,
                        f'{VOCAB_URI}shape',
                        _literal(quantity.shape, datatype=f'{XSD_NS}string'),
                    )
                )
            if quantity.unit:
                triples.append(
                    RDFTriple(
                        property_uri,
                        f'{VOCAB_URI}unit',
                        _literal(quantity.unit, datatype=f'{XSD_NS}string'),
                    )
                )
            for enum_value in quantity.enum_values:
                triples.append(
                    RDFTriple(
                        property_uri,
                        f'{VOCAB_URI}enumValue',
                        _literal(enum_value),
                    )
                )

        for sub_section in section.sub_sections:
            property_uri = _source_property_uri(
                section, sub_section.name, base_uri, kind='subsection'
            )
            triples.append(
                RDFTriple(section_uri, f'{VOCAB_URI}definesProperty', _resource(property_uri))
            )
            triples.extend(
                [
                    RDFTriple(property_uri, f'{RDF_NS}type', _resource(f'{OWL_NS}ObjectProperty')),
                    RDFTriple(property_uri, f'{RDFS_NS}label', _literal(sub_section.name)),
                    RDFTriple(property_uri, f'{RDFS_NS}domain', _resource(section_uri)),
                    RDFTriple(property_uri, f'{VOCAB_URI}propertyKind', _literal('subsection')),
                    RDFTriple(
                        property_uri,
                        f'{VOCAB_URI}repeats',
                        _literal(
                            str(sub_section.repeats).lower(), datatype=f'{XSD_NS}boolean'
                        ),
                    ),
                ]
            )
            if sub_section.description:
                triples.append(
                    RDFTriple(property_uri, f'{RDFS_NS}comment', _literal(sub_section.description))
                )
            target_section = (
                section_by_name.get(sub_section.target_name)
                if sub_section.target_name is not None
                else None
            )
            if target_section is not None:
                target_uri = _source_section_uri(target_section, base_uri)
                triples.extend(
                    [
                        RDFTriple(property_uri, f'{RDFS_NS}range', _resource(target_uri)),
                        RDFTriple(section_uri, f'{VOCAB_URI}hasSubSection', _resource(target_uri)),
                    ]
                )

    return sorted(set(triples))


def _iter_base_section_classes(section_cls: type) -> Iterator[type]:
    section_def = getattr(section_cls, 'm_def', None)
    if section_def is None:
        return

    seen: set[str] = set()
    base_sections = getattr(section_def, 'all_base_sections', None)
    if base_sections is None:
        base_sections = getattr(section_def, 'base_sections', None)

    for base_section in _iter_defs(base_sections):
        base_cls = _as_section_cls(base_section)
        if base_cls is None:
            continue
        qualified_name = _qualified_class_name(base_cls)
        if qualified_name in seen:
            continue
        seen.add(qualified_name)
        yield base_cls


def _iter_quantities(section_cls: type) -> Iterator[Any]:
    section_def = getattr(section_cls, 'm_def', None)
    if section_def is None:
        return
    quantities = getattr(section_def, 'all_quantities', None)
    if quantities is None:
        quantities = getattr(section_def, 'quantities', None)
    yield from _iter_defs(quantities)


def _iter_subsections(section_cls: type) -> Iterator[Any]:
    section_def = getattr(section_cls, 'm_def', None)
    if section_def is None:
        return
    sub_sections = getattr(section_def, 'all_sub_sections', None)
    if sub_sections is None:
        sub_sections = getattr(section_def, 'sub_sections', None)
    yield from _iter_defs(sub_sections)


def _range_resource(type_hint: Any, base_uri: str) -> tuple[str | None, list[RDFTriple]]:
    flattened_types = [
        candidate
        for candidate in _flatten_types(type_hint)
        if candidate is not type(None)
    ] or [type_hint]

    for candidate in flattened_types:
        section_cls = _as_section_cls(candidate)
        if section_cls is not None:
            return _section_uri(section_cls, base_uri), []

    type_name = _type_name(flattened_types[0])
    if type_name == 'Any':
        return f'{RDFS_NS}Literal', []
    if type_name in {'str', 'm_str'}:
        return f'{XSD_NS}string', []
    if type_name in {'bool'}:
        return f'{XSD_NS}boolean', []
    if type_name in {'int', 'int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64'}:
        return f'{XSD_NS}integer', []
    if type_name in {'float', 'float16', 'float32', 'float64'}:
        return f'{XSD_NS}double', []
    if type_name in {'Datetime', 'datetime'}:
        return f'{XSD_NS}dateTime', []
    if type_name in {'MEnum'}:
        return f'{XSD_NS}string', []

    datatype_uri = _datatype_uri(flattened_types[0], base_uri)
    datatype_triples = [
        RDFTriple(datatype_uri, f'{RDF_NS}type', _resource(f'{RDFS_NS}Datatype')),
        RDFTriple(datatype_uri, f'{RDFS_NS}label', _literal(type_name)),
    ]
    return datatype_uri, datatype_triples


def _stringify_shape(shape: Any) -> str | None:
    if not shape:
        return None
    if isinstance(shape, (list, tuple)):
        return json.dumps(list(shape))
    return str(shape)


def _vocab_triples() -> list[RDFTriple]:
    properties = {
        'definesProperty': 'Connects a section class to one of its schema properties.',
        'hasSubSection': 'Connects a section class to the class used as a subsection.',
        'propertyKind': 'Marks whether a schema property came from a quantity or subsection.',
        'shape': 'Stores the NOMAD quantity shape declaration.',
        'unit': 'Stores the NOMAD unit declaration as text.',
        'repeats': 'Indicates whether a subsection repeats.',
        'pythonModule': 'Python module that defines the schema class.',
        'pythonClass': 'Fully qualified Python class name for the schema class.',
        'enumValue': 'Enumeration member available for an enum-backed quantity.',
    }
    triples: list[RDFTriple] = []
    for name, description in properties.items():
        iri = f'{VOCAB_URI}{name}'
        triples.extend(
            [
                RDFTriple(iri, f'{RDF_NS}type', _resource(f'{RDF_NS}Property')),
                RDFTriple(iri, f'{RDFS_NS}label', _literal(name)),
                RDFTriple(iri, f'{RDFS_NS}comment', _literal(description)),
            ]
        )
    return triples


def section_classes_to_rdf_triples(
    section_classes: Iterable[type], base_uri: str = DEFAULT_BASE_URI
) -> list[RDFTriple]:
    """
    Convert section classes into RDF triples.
    """
    triples: list[RDFTriple] = _vocab_triples()

    for section_cls in sorted(
        set(section_classes), key=lambda cls: _qualified_class_name(cls)
    ):
        section_def = getattr(section_cls, 'm_def', None)
        if section_def is None:
            continue

        section_uri = _section_uri(section_cls, base_uri)
        qualified_name = _qualified_class_name(section_cls)

        triples.extend(
            [
                RDFTriple(section_uri, f'{RDF_NS}type', _resource(f'{OWL_NS}Class')),
                RDFTriple(section_uri, f'{RDFS_NS}label', _literal(section_cls.__name__)),
                RDFTriple(
                    section_uri,
                    f'{VOCAB_URI}pythonModule',
                    _literal(section_cls.__module__),
                ),
                RDFTriple(
                    section_uri,
                    f'{VOCAB_URI}pythonClass',
                    _literal(qualified_name),
                ),
            ]
        )

        description = _description_for(section_def) or _description_for(section_cls)
        if description:
            triples.append(RDFTriple(section_uri, f'{RDFS_NS}comment', _literal(description)))

        for link in _iter_links(section_def):
            triples.append(RDFTriple(section_uri, f'{RDFS_NS}seeAlso', _resource(link)))

        for base_cls in _iter_base_section_classes(section_cls):
            triples.append(
                RDFTriple(
                    section_uri,
                    f'{RDFS_NS}subClassOf',
                    _resource(_section_uri(base_cls, base_uri)),
                )
            )

        for quantity in _iter_quantities(section_cls):
            quantity_name = getattr(quantity, 'name', None)
            if not quantity_name:
                continue

            property_uri = _property_uri(section_cls, quantity_name, base_uri, kind='quantity')
            triples.append(
                RDFTriple(section_uri, f'{VOCAB_URI}definesProperty', _resource(property_uri))
            )

            range_uri, range_triples = _range_resource(getattr(quantity, 'type', Any), base_uri)
            triples.extend(range_triples)

            property_type = (
                f'{OWL_NS}ObjectProperty'
                if range_uri and range_uri.startswith(_join_iri(base_uri, 'section/'))
                else f'{OWL_NS}DatatypeProperty'
            )
            triples.extend(
                [
                    RDFTriple(property_uri, f'{RDF_NS}type', _resource(property_type)),
                    RDFTriple(property_uri, f'{RDFS_NS}label', _literal(quantity_name)),
                    RDFTriple(property_uri, f'{RDFS_NS}domain', _resource(section_uri)),
                    RDFTriple(property_uri, f'{VOCAB_URI}propertyKind', _literal('quantity')),
                ]
            )
            if range_uri:
                triples.append(
                    RDFTriple(property_uri, f'{RDFS_NS}range', _resource(range_uri))
                )

            description = _description_for(quantity)
            if description:
                triples.append(
                    RDFTriple(property_uri, f'{RDFS_NS}comment', _literal(description))
                )

            if shape := _stringify_shape(getattr(quantity, 'shape', None)):
                triples.append(
                    RDFTriple(
                        property_uri,
                        f'{VOCAB_URI}shape',
                        _literal(shape, datatype=f'{XSD_NS}string'),
                    )
                )

            unit = getattr(quantity, 'unit', None)
            if unit is not None:
                triples.append(
                    RDFTriple(
                        property_uri,
                        f'{VOCAB_URI}unit',
                        _literal(str(unit), datatype=f'{XSD_NS}string'),
                    )
                )

            quantity_type = _resolved(getattr(quantity, 'type', None))
            if _type_name(quantity_type) == 'MEnum':
                try:
                    enum_values = list(quantity_type)
                except Exception:
                    enum_values = []
                for enum_value in enum_values:
                    triples.append(
                        RDFTriple(
                            property_uri,
                            f'{VOCAB_URI}enumValue',
                            _literal(str(enum_value)),
                        )
                    )

        for sub_section in _iter_subsections(section_cls):
            sub_section_name = getattr(sub_section, 'name', None)
            if not sub_section_name:
                continue

            child_cls = _as_section_cls(getattr(sub_section, 'sub_section', None))
            if child_cls is None:
                child_cls = _as_section_cls(getattr(sub_section, 'section_def', None))

            property_uri = _property_uri(
                section_cls, sub_section_name, base_uri, kind='subsection'
            )
            triples.append(
                RDFTriple(section_uri, f'{VOCAB_URI}definesProperty', _resource(property_uri))
            )
            triples.extend(
                [
                    RDFTriple(
                        property_uri, f'{RDF_NS}type', _resource(f'{OWL_NS}ObjectProperty')
                    ),
                    RDFTriple(property_uri, f'{RDFS_NS}label', _literal(sub_section_name)),
                    RDFTriple(property_uri, f'{RDFS_NS}domain', _resource(section_uri)),
                    RDFTriple(
                        property_uri, f'{VOCAB_URI}propertyKind', _literal('subsection')
                    ),
                    RDFTriple(
                        property_uri,
                        f'{VOCAB_URI}repeats',
                        _literal(
                            str(bool(getattr(sub_section, 'repeats', False))).lower(),
                            datatype=f'{XSD_NS}boolean',
                        ),
                    ),
                ]
            )

            if child_cls is not None:
                child_uri = _section_uri(child_cls, base_uri)
                triples.extend(
                    [
                        RDFTriple(property_uri, f'{RDFS_NS}range', _resource(child_uri)),
                        RDFTriple(section_uri, f'{VOCAB_URI}hasSubSection', _resource(child_uri)),
                    ]
                )

            description = _description_for(sub_section)
            if description:
                triples.append(
                    RDFTriple(property_uri, f'{RDFS_NS}comment', _literal(description))
                )

    return sorted(set(triples))


def section_classes_to_rdf_turtle(
    section_classes: Iterable[type], base_uri: str = DEFAULT_BASE_URI
) -> str:
    return serialize_turtle(
        section_classes_to_rdf_triples(section_classes, base_uri=base_uri),
        base_uri=base_uri,
    )


def schema_package_to_rdf_triples(
    package: str = DEFAULT_SCHEMA_PACKAGE, base_uri: str = DEFAULT_BASE_URI
) -> list[RDFTriple]:
    try:
        return section_classes_to_rdf_triples(
            discover_schema_section_classes(package=package), base_uri=base_uri
        )
    except Exception:
        return source_package_to_rdf_triples(package=package, base_uri=base_uri)


def schema_package_to_rdf_turtle(
    package: str = DEFAULT_SCHEMA_PACKAGE, base_uri: str = DEFAULT_BASE_URI
) -> str:
    return serialize_turtle(
        schema_package_to_rdf_triples(package=package, base_uri=base_uri),
        base_uri=base_uri,
    )


def write_schema_package_rdf(
    output_path: str | Path,
    package: str = DEFAULT_SCHEMA_PACKAGE,
    base_uri: str = DEFAULT_BASE_URI,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        schema_package_to_rdf_turtle(package=package, base_uri=base_uri),
        encoding='utf-8',
    )
    return output


__all__ = [
    'DEFAULT_BASE_URI',
    'DEFAULT_SCHEMA_PACKAGE',
    'RDFNode',
    'RDFTriple',
    'discover_schema_section_classes',
    'schema_package_to_rdf_triples',
    'schema_package_to_rdf_turtle',
    'section_classes_to_rdf_triples',
    'section_classes_to_rdf_turtle',
    'source_package_to_rdf_triples',
    'serialize_turtle',
    'write_schema_package_rdf',
]
