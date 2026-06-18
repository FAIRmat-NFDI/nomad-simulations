from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from urllib.parse import quote

from nomad_simulations.rdf import (
    DEFAULT_BASE_URI,
    discover_schema_section_classes,
    section_classes_to_rdf_triples,
    section_classes_to_rdf_turtle,
    write_schema_package_rdf,
)


@dataclass
class FakeQuantity:
    name: str
    type: object
    description: str | None = None
    shape: list[object] = field(default_factory=list)
    unit: object | None = None


@dataclass
class FakeSubSection:
    name: str
    sub_section: object
    repeats: bool = False
    description: str | None = None


@dataclass
class FakeSectionDef:
    name: str
    description: str | None = None
    links: list[str] = field(default_factory=list)
    all_quantities: dict[str, FakeQuantity] = field(default_factory=dict)
    all_sub_sections: dict[str, FakeSubSection] = field(default_factory=dict)
    all_base_sections: list[object] = field(default_factory=list)


def _make_fake_sections():
    class FakeCustomType:
        pass

    BaseSimulation = type(
        'BaseSimulation',
        (),
        {
            '__module__': 'nomad_simulations.schema_packages.general',
            '__doc__': 'A shared base simulation section.',
        },
    )
    ModelSystem = type(
        'ModelSystem',
        (),
        {
            '__module__': 'nomad_simulations.schema_packages.model_system',
            '__doc__': 'Represents a model system.',
        },
    )
    Simulation = type(
        'Simulation',
        (BaseSimulation,),
        {
            '__module__': 'nomad_simulations.schema_packages.general',
            '__doc__': 'A concrete simulation section.',
        },
    )

    BaseSimulation.m_def = FakeSectionDef(
        name='BaseSimulation',
        description='A shared base simulation section.',
    )
    ModelSystem.m_def = FakeSectionDef(
        name='ModelSystem',
        description='Represents a model system.',
    )
    Simulation.m_def = FakeSectionDef(
        name='Simulation',
        description='A concrete simulation section.',
        links=['https://example.org/schema/Simulation'],
        all_quantities={
            'finished_without_errors': FakeQuantity(
                name='finished_without_errors',
                type=bool,
                description='Whether the simulation finished successfully.',
            ),
            'total_energy': FakeQuantity(
                name='total_energy',
                type=FakeCustomType(),
                description='The total energy.',
                shape=['0..*'],
                unit='joule',
            ),
            'model_system_ref': FakeQuantity(
                name='model_system_ref',
                type=ModelSystem,
                description='Reference to the representative model system.',
            ),
        },
        all_sub_sections={
            'model_systems': FakeSubSection(
                name='model_systems',
                sub_section=ModelSystem,
                repeats=True,
                description='Contained model systems.',
            )
        },
        all_base_sections=[BaseSimulation],
    )

    return BaseSimulation, ModelSystem, Simulation


def test_section_classes_to_rdf_triples_captures_schema_structure():
    base_simulation, model_system, simulation = _make_fake_sections()

    triples = section_classes_to_rdf_triples(
        [base_simulation, model_system, simulation]
    )
    triple_set = {
        (triple.subject, triple.predicate, triple.object.value) for triple in triples
    }

    simulation_uri = (
        f'{DEFAULT_BASE_URI}section/'
        f'{quote("nomad_simulations.schema_packages.general.Simulation", safe="")}'
    )
    base_simulation_uri = (
        f'{DEFAULT_BASE_URI}section/'
        f'{quote("nomad_simulations.schema_packages.general.BaseSimulation", safe="")}'
    )
    model_system_uri = (
        f'{DEFAULT_BASE_URI}section/'
        f'{quote("nomad_simulations.schema_packages.model_system.ModelSystem", safe="")}'
    )
    finished_uri = (
        f'{DEFAULT_BASE_URI}quantity/'
        f'{quote("nomad_simulations.schema_packages.general.Simulation", safe="")}/'
        f'{quote("finished_without_errors", safe="")}'
    )
    energy_uri = (
        f'{DEFAULT_BASE_URI}quantity/'
        f'{quote("nomad_simulations.schema_packages.general.Simulation", safe="")}/'
        f'{quote("total_energy", safe="")}'
    )
    model_ref_uri = (
        f'{DEFAULT_BASE_URI}quantity/'
        f'{quote("nomad_simulations.schema_packages.general.Simulation", safe="")}/'
        f'{quote("model_system_ref", safe="")}'
    )
    subsection_uri = (
        f'{DEFAULT_BASE_URI}subsection/'
        f'{quote("nomad_simulations.schema_packages.general.Simulation", safe="")}/'
        f'{quote("model_systems", safe="")}'
    )
    custom_datatype_uri = (
        f'{DEFAULT_BASE_URI}datatype/{quote("FakeCustomType", safe="")}'
    )

    assert (
        simulation_uri,
        'http://www.w3.org/2000/01/rdf-schema#subClassOf',
        base_simulation_uri,
    ) in triple_set
    assert (
        finished_uri,
        'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
        'http://www.w3.org/2002/07/owl#DatatypeProperty',
    ) in triple_set
    assert (
        finished_uri,
        'http://www.w3.org/2000/01/rdf-schema#range',
        'http://www.w3.org/2001/XMLSchema#boolean',
    ) in triple_set
    assert (
        model_ref_uri,
        'http://www.w3.org/2000/01/rdf-schema#range',
        model_system_uri,
    ) in triple_set
    assert (
        subsection_uri,
        'http://www.w3.org/2000/01/rdf-schema#range',
        model_system_uri,
    ) in triple_set
    assert (
        energy_uri,
        'https://fairmat-nfdi.github.io/nomad-simulations/vocab/unit',
        'joule',
    ) in triple_set
    assert (
        energy_uri,
        'http://www.w3.org/2000/01/rdf-schema#range',
        custom_datatype_uri,
    ) in triple_set
    assert (
        custom_datatype_uri,
        'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
        'http://www.w3.org/2000/01/rdf-schema#Datatype',
    ) in triple_set


def test_section_classes_to_rdf_turtle_is_deterministic_and_serializes_literals():
    _, _, simulation = _make_fake_sections()
    simulation.m_def.description = 'A "quoted"\nsection description.\f\x01'

    turtle = section_classes_to_rdf_turtle([simulation])

    assert (
        '@prefix ns: <https://fairmat-nfdi.github.io/nomad-simulations/rdf/> .'
        in turtle
    )
    assert 'owl:Class' in turtle
    assert 'owl:DatatypeProperty' in turtle
    assert 'owl:ObjectProperty' in turtle
    assert '\\"quoted\\"\\nsection description.\\f\\u0001' in turtle
    assert 'nomad:repeats "true"^^xsd:boolean' in turtle
    assert 'nomad:shape "[\\"0..*\\"]"^^xsd:string' in turtle
    assert 'rdfs:seeAlso <https://example.org/schema/Simulation>' in turtle
    assert 'nomad:hasSubSection' not in turtle


def test_subsection_comments_require_explicit_property_descriptions():
    _, model_system, simulation = _make_fake_sections()

    class GenericFrameworkSubSection:
        """Generic framework subsection documentation."""

        def __init__(self, name: str, sub_section: object, repeats: bool = False):
            self.name = name
            self.sub_section = sub_section
            self.repeats = repeats
            self.description = None

    simulation.m_def.all_sub_sections['undocumented_child'] = (
        GenericFrameworkSubSection(
            name='undocumented_child',
            sub_section=model_system,
        )
    )

    triples = section_classes_to_rdf_triples([simulation])
    triple_set = {
        (triple.subject, triple.predicate, triple.object.value) for triple in triples
    }

    documented_uri = (
        f'{DEFAULT_BASE_URI}subsection/'
        f'{quote("nomad_simulations.schema_packages.general.Simulation", safe="")}/'
        f'{quote("model_systems", safe="")}'
    )
    undocumented_uri = (
        f'{DEFAULT_BASE_URI}subsection/'
        f'{quote("nomad_simulations.schema_packages.general.Simulation", safe="")}/'
        f'{quote("undocumented_child", safe="")}'
    )

    assert (
        documented_uri,
        'http://www.w3.org/2000/01/rdf-schema#comment',
        'Contained model systems.',
    ) in triple_set
    assert not any(
        subject == undocumented_uri
        and predicate == 'http://www.w3.org/2000/01/rdf-schema#comment'
        for subject, predicate, _ in triple_set
    )


def test_discover_schema_section_classes_uses_minimal_reachable_closure(monkeypatch):
    class FakeMSection:
        pass

    ExternalBase = type(
        'ExternalBase',
        (FakeMSection,),
        {'__module__': 'nomad.datamodel.external'},
    )
    ExternalReference = type(
        'ExternalReference',
        (FakeMSection,),
        {'__module__': 'nomad.datamodel.external'},
    )
    ImportedNoise = type(
        'ImportedNoise',
        (FakeMSection,),
        {'__module__': 'nomad.datamodel.external'},
    )
    LocalSimulation = type(
        'LocalSimulation',
        (ExternalBase,),
        {'__module__': 'nomad_simulations.schema_packages.fake'},
    )

    ExternalBase.m_def = FakeSectionDef(name='ExternalBase')
    ExternalReference.m_def = FakeSectionDef(name='ExternalReference')
    ImportedNoise.m_def = FakeSectionDef(name='ImportedNoise')
    LocalSimulation.m_def = FakeSectionDef(
        name='LocalSimulation',
        all_quantities={
            'external_ref': FakeQuantity(
                name='external_ref',
                type=ExternalReference,
            )
        },
        all_base_sections=[ExternalBase],
    )

    fake_package = types.SimpleNamespace(__name__='nomad_simulations.schema_packages')
    fake_module = types.SimpleNamespace(
        LocalSimulation=LocalSimulation,
        ImportedNoise=ImportedNoise,
    )
    fake_metainfo = types.ModuleType('nomad.metainfo')
    fake_metainfo.MSection = FakeMSection

    def fake_import_module(name: str):
        if name == 'nomad.metainfo':
            return fake_metainfo
        if name == 'nomad_simulations.schema_packages':
            return fake_package
        raise ImportError(name)

    monkeypatch.setattr(
        'nomad_simulations.rdf.ensure_nomad_datamodel_compat', lambda: None
    )
    monkeypatch.setattr(
        'nomad_simulations.rdf.importlib.import_module', fake_import_module
    )
    monkeypatch.setattr(
        'nomad_simulations.rdf._iter_modules_recursively',
        lambda root: iter([fake_module]),
    )
    monkeypatch.setitem(sys.modules, 'nomad.metainfo', fake_metainfo)

    discovered = discover_schema_section_classes()

    assert LocalSimulation in discovered
    assert ExternalBase in discovered
    assert ExternalReference in discovered
    assert ImportedNoise not in discovered


def test_write_schema_package_rdf_writes_output(monkeypatch, tmp_path):
    _, _, simulation = _make_fake_sections()

    def _discover(package: str):
        assert package == 'nomad_simulations.schema_packages'
        return [simulation]

    monkeypatch.setattr(
        'nomad_simulations.rdf.discover_schema_section_classes',
        _discover,
    )

    output_path = tmp_path / 'schema.ttl'
    written_path = write_schema_package_rdf(output_path)

    assert written_path == output_path
    assert output_path.exists()
    assert 'Simulation' in output_path.read_text(encoding='utf-8')


def test_generated_schema_turtle_parses_with_rdflib(tmp_path):
    from rdflib import Graph

    output_path = tmp_path / 'schema.ttl'
    write_schema_package_rdf(output_path)

    turtle = output_path.read_text(encoding='utf-8')
    assert 'nomad_simulations.schema_packages.basis_set.APWOrbital' in turtle
    assert 'nomad.datamodel.metainfo.workflow.Workflow' in turtle
    assert 'nomad.datamodel.datamodel.EntryArchive' not in turtle
    assert all(ord(char) >= 32 or char in '\n\r\t' for char in turtle)
    assert 'nomad:hasSubSection' not in turtle
    assert (
        'Like quantities, subsections are defined in a `section class` as attributes'
        not in turtle
    )

    graph = Graph()
    graph.parse(str(output_path), format='turtle')

    assert len(graph) > 0
