import logging

import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.model_method import (
    DFT,
    HamiltonianTerm,
    ModelMethod,
    ModelMethodElectronic,
    RelativityModel,
)
from nomad_simulations.schema_packages.utils import (
    LegacyCleanupStats,
    cleanup_archive,
    is_self_duplicate,
    resolve_legacy_contributions,
)

from .. import logger
from ..conftest import generate_simulation


def test_relativity_relocated_from_contributions(caplog):
    """
    Legacy archives store `RelativityModel` under `contributions`; it is relocated
    to the typed `relativity` subsection (object identity preserved) and stays there
    on repeated cleanup.
    """
    rel = RelativityModel(level='scalar')
    method = ModelMethodElectronic(contributions=[rel])

    with caplog.at_level(logging.WARNING):
        stats = resolve_legacy_contributions(method, logger)

    assert len(method.contributions) == 0
    assert method.relativity is rel
    assert 'Relocated' in caplog.text
    assert stats.n_relocated_relativity == 1
    assert stats.changed

    stats = resolve_legacy_contributions(method, logger)

    assert len(method.contributions) == 0
    assert method.relativity is rel
    assert not stats.changed


def test_relativity_relocation_conflict_keeps_data(caplog):
    """
    If `relativity` is already populated, the legacy contribution stays in place
    (no data loss) and warnings are emitted.
    """
    method = ModelMethodElectronic(relativity=RelativityModel(level='scalar'))
    second = RelativityModel(level='two-component')
    method.m_add_sub_section(type(method).contributions, second)

    with caplog.at_level(logging.WARNING):
        stats = resolve_legacy_contributions(method, logger)

    assert method.relativity.level == 'scalar'
    assert len(method.contributions) == 1
    assert method.contributions[0] is second
    assert 'no free `relativity` subsection' in caplog.text
    assert stats.n_blocked_relocations == 1
    assert not stats.changed


def test_relativity_in_plain_model_method_stays_with_warning(caplog):
    """
    Plain `ModelMethod` has no `relativity` subsection; the entry stays in
    `contributions` and the non-term residual warning is emitted.
    """
    method = ModelMethod(contributions=[RelativityModel(level='scalar')])

    with caplog.at_level(logging.WARNING):
        stats = resolve_legacy_contributions(method, logger)

    assert len(method.contributions) == 1
    assert 'HamiltonianTerm' in caplog.text
    assert stats.n_blocked_relocations == 1
    assert stats.n_residual_non_terms == 1


def test_contributions_self_duplicate_pruned(caplog):
    """
    An exact self-copy nested in `contributions` (recursive-mapping parser artifact
    in legacy archives) is pruned, including multi-level copies.
    """
    innermost = DFT(name='X')
    middle = DFT(name='X')
    middle.contributions.append(innermost)
    parent = DFT(name='X')
    parent.contributions.append(middle)

    with caplog.at_level(logging.WARNING):
        stats = resolve_legacy_contributions(parent, logger)

    assert len(parent.contributions) == 0
    assert 'self-duplicate' in caplog.text
    assert stats.n_pruned_duplicates == 1
    assert stats.changed


def test_contributions_non_duplicate_method_retained(caplog):
    """
    A nested method that differs from the parent is not pruned (additive invariant);
    only the non-term residual warning is emitted.
    """
    parent = DFT(name='X')
    parent.contributions.append(DFT(name='Y'))

    with caplog.at_level(logging.WARNING):
        stats = resolve_legacy_contributions(parent, logger)

    assert len(parent.contributions) == 1
    assert parent.contributions[0].name == 'Y'
    assert 'HamiltonianTerm' in caplog.text
    assert stats.n_pruned_duplicates == 0
    assert stats.n_residual_non_terms == 1


@pytest.mark.parametrize(
    'parent_factory, contribution_factory, expected',
    [
        # exact copy of the same class
        (lambda: DFT(name='X'), lambda: DFT(name='X'), True),
        # same class, different content
        (lambda: DFT(name='X'), lambda: DFT(name='Y'), False),
        # different class, same content
        (lambda: ModelMethod(name='X'), lambda: ModelMethodElectronic(name='X'), False),
    ],
)
def test_is_self_duplicate(parent_factory, contribution_factory, expected):
    parent = parent_factory()
    contribution = contribution_factory()
    parent.contributions.append(contribution)

    assert is_self_duplicate(parent, contribution) is expected


def test_stats_merge_and_to_dict():
    total = LegacyCleanupStats()
    total.merge(LegacyCleanupStats(n_methods_visited=1, n_pruned_duplicates=2))
    total.merge(LegacyCleanupStats(n_methods_visited=1, n_relocated_relativity=1))

    assert total.n_methods_visited == 2
    assert total.changed
    assert total.to_dict() == {
        'n_methods_visited': 2,
        'n_pruned_duplicates': 2,
        'n_relocated_relativity': 1,
        'n_blocked_relocations': 0,
        'n_residual_non_terms': 0,
    }


def test_cleanup_archive_aggregates_across_methods():
    """
    The archive-level driver visits every `ModelMethod`, mutates in place, and
    aggregates the per-method stats.
    """
    duplicated = DFT(name='X')
    duplicated.contributions.append(DFT(name='X'))
    with_relativity = ModelMethodElectronic(
        contributions=[RelativityModel(level='scalar')]
    )
    archive = EntryArchive(
        data=generate_simulation(model_method=[duplicated, with_relativity])
    )

    stats = cleanup_archive(archive, logger)

    assert stats.n_methods_visited == 2
    assert stats.n_pruned_duplicates == 1
    assert stats.n_relocated_relativity == 1
    assert stats.changed
    assert len(duplicated.contributions) == 0
    assert with_relativity.relativity is not None


def test_cleanup_archive_noop():
    archive = EntryArchive(
        data=generate_simulation(
            model_method=[ModelMethod(contributions=[HamiltonianTerm(name='kinetic')])]
        )
    )

    stats = cleanup_archive(archive, logger)

    assert stats.n_methods_visited == 1
    assert not stats.changed
    assert stats.to_dict()['n_pruned_duplicates'] == 0


def test_cleanup_archive_skips_methods_detached_by_pruning():
    """
    A nested method removed as a self-duplicate must not be re-visited (its own
    cleanup would double-count stats).
    """
    child = DFT(name='X')
    parent = DFT(name='X')
    parent.contributions.append(child)
    archive = EntryArchive(data=generate_simulation(model_method=[parent]))

    stats = cleanup_archive(archive, logger)

    assert stats.n_pruned_duplicates == 1
    # only the parent is counted; the pruned child is skipped
    assert stats.n_methods_visited == 1
