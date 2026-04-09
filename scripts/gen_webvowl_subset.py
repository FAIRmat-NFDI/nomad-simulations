from __future__ import annotations

import argparse
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

DEFAULT_INPUT = Path('schema.ttl')
DEFAULT_OUTPUT = Path('schema-webvowl.ttl')
DEFAULT_PACKAGE = 'nomad_simulations.schema_packages'
DEFAULT_ONTOLOGY_IRI = (
    'https://fairmat-nfdi.github.io/nomad-simulations/rdf/webvowl-subset'
)

NS = Namespace('https://fairmat-nfdi.github.io/nomad-simulations/rdf/')
VOC = Namespace('https://fairmat-nfdi.github.io/nomad-simulations/vocab/')


def _module_name(graph: Graph, resource: URIRef) -> str | None:
    value = graph.value(resource, VOC.pythonModule)
    return str(value) if isinstance(value, Literal) else None


def _is_section(resource: URIRef) -> bool:
    return str(resource).startswith(f'{NS}section/')


def _is_local_section(graph: Graph, resource: URIRef, package: str) -> bool:
    module_name = _module_name(graph, resource)
    return bool(module_name and module_name.startswith(f'{package}.'))


def _copy_optional_annotations(source: Graph, target: Graph, resource: URIRef) -> None:
    for predicate in (RDFS.label, RDFS.comment, VOC.pythonModule, VOC.pythonClass):
        for obj in source.objects(resource, predicate):
            target.add((resource, predicate, obj))


def build_webvowl_subset(
    source: Graph,
    package: str = DEFAULT_PACKAGE,
    ontology_iri: str = DEFAULT_ONTOLOGY_IRI,
) -> Graph:
    target = Graph()
    target.bind('rdf', RDF)
    target.bind('rdfs', RDFS)
    target.bind('owl', OWL)
    target.bind('nomad', VOC)
    target.bind('ns', NS)

    ontology = URIRef(ontology_iri)
    target.add((ontology, RDF.type, OWL.Ontology))
    target.add(
        (
            ontology,
            RDFS.label,
            Literal('nomad-simulations WebVOWL subset'),
        )
    )

    local_classes = {
        section
        for section in source.subjects(RDF.type, OWL.Class)
        if isinstance(section, URIRef)
        and _is_section(section)
        and _is_local_section(source, section, package)
    }

    kept_classes = set(local_classes)
    subclass_edges: set[tuple[URIRef, URIRef]] = set()
    object_properties: set[URIRef] = set()

    for section in local_classes:
        for parent in source.objects(section, RDFS.subClassOf):
            if isinstance(parent, URIRef) and _is_section(parent):
                kept_classes.add(parent)
                subclass_edges.add((section, parent))

    for prop in source.subjects(RDF.type, OWL.ObjectProperty):
        if not isinstance(prop, URIRef):
            continue

        domain = source.value(prop, RDFS.domain)
        range_ = source.value(prop, RDFS.range)
        if not isinstance(domain, URIRef) or not isinstance(range_, URIRef):
            continue
        if domain not in local_classes:
            continue
        if not _is_section(range_):
            continue

        object_properties.add(prop)
        kept_classes.add(range_)

    for section in kept_classes:
        target.add((section, RDF.type, OWL.Class))
        _copy_optional_annotations(source, target, section)

    for child, parent in sorted(subclass_edges):
        if child in kept_classes and parent in kept_classes:
            target.add((child, RDFS.subClassOf, parent))

    for prop in sorted(object_properties):
        target.add((prop, RDF.type, OWL.ObjectProperty))
        for predicate in (
            RDFS.label,
            RDFS.comment,
            RDFS.domain,
            RDFS.range,
            VOC.propertyKind,
            VOC.repeats,
        ):
            for obj in source.objects(prop, predicate):
                target.add((prop, predicate, obj))

    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Create a smaller Turtle subset optimized for WebVOWL.'
    )
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--package', default=DEFAULT_PACKAGE)
    args = parser.parse_args()

    source = Graph()
    source.parse(str(args.input), format='turtle')

    subset = build_webvowl_subset(source, package=args.package)
    serialized = subset.serialize(format='turtle')
    if isinstance(serialized, bytes):
        serialized = serialized.decode('utf-8')
    args.output.write_text(serialized, encoding='utf-8')


if __name__ == '__main__':
    main()
