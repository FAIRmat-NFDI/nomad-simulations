import json
from importlib.resources import files

from nomad_simulations.schema_packages.utils.basis_set_exchange import (
    registry as basis_set_registry,
)
from nomad_simulations.schema_packages.utils.basis_set_exchange.build import (
    spec_from_label,
)


def test_exact_canonical_label_lookup():
    rec = basis_set_registry.lookup_by_label('cc-pVDZ')

    assert rec is not None
    assert rec['canonical_key'] == 'cc-pvdz'
    assert rec['canonical_name'] == 'cc-pVDZ'


def test_relaxed_case_insensitive_lookup():
    rec = basis_set_registry.lookup_by_label(' Def2 SVP ')

    assert rec is not None
    assert rec['canonical_key'] == 'def2-svp'
    assert rec['canonical_name'] == 'def2-SVP'


def test_parenthesized_names_remain_distinct_under_relaxed_lookup():
    svp = basis_set_registry.lookup_by_label('Def2 SVP')
    sv_p = basis_set_registry.lookup_by_label('def2 SV(P)')

    assert svp is not None
    assert sv_p is not None
    assert svp['canonical_name'] == 'def2-SVP'
    assert sv_p['canonical_name'] == 'def2-SV(P)'


def test_pople_star_and_parenthesized_labels_are_distinct_canonical_entries():
    parenthesized = basis_set_registry.lookup_by_label('6-31G(d,p)')
    starred = basis_set_registry.lookup_by_label('6-31G**')

    assert parenthesized is not None
    assert starred is not None
    assert parenthesized['canonical_key'] == '6-31g(d,p)'
    assert starred['canonical_key'] == '6-31g_st__st_'


def test_unknown_basis_set_returns_none():
    assert basis_set_registry.lookup_by_label('not-a-real-basis-set') is None
    assert spec_from_label('not-a-real-basis-set') is None


def test_ambiguous_alias_returns_none():
    assert basis_set_registry.lookup_by_label('Pople polarized') is None
    assert spec_from_label('Pople polarized') is None


def test_spec_from_label_returns_internal_canonical_record():
    spec = spec_from_label('sto 3g')

    assert spec == {
        'canonical_name': 'STO-3G',
    }


def test_registry_contains_full_bse_name_export_shape():
    path = files('nomad_simulations.schema_packages.utils.basis_set_exchange').joinpath(
        'registry_min.json'
    )
    data = json.loads(path.read_text(encoding='utf-8'))

    assert len(data) > 700
    assert all(set(row) == {'key', 'canonical_name', 'aliases'} for row in data)


def test_registry_provenance_is_module_level_metadata():
    assert basis_set_registry.source_name() == 'Basis Set Exchange'
    assert basis_set_registry.registry_version() == 'basis-set-exchange-0.12'
