"""
Cleanup of legacy `ModelMethod.contributions` content that predates the
`HamiltonianTerm` typing: exact self-duplicate nested methods (an artifact of
recursive mapping-parser annotations), `RelativityModel` entries that belong in the
typed `relativity` subsection, and residual non-term entries.

The cleanup is idempotent: re-running it on an already-cleaned archive is a no-op,
so callers (e.g. Temporal activity retries) may safely apply it repeatedly.

Schema classes are imported lazily inside the functions: `model_method.py` imports
from this `utils` package, so module-level imports here would be circular.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

    from nomad_simulations.schema_packages.model_method import (
        BaseModelMethod,
        ModelMethod,
    )


@dataclass
class LegacyCleanupStats:
    """
    Machine-readable outcome of a legacy-`contributions` cleanup run.
    """

    n_methods_visited: int = 0
    n_pruned_duplicates: int = 0
    n_relocated_relativity: int = 0
    n_blocked_relocations: int = 0
    n_residual_non_terms: int = 0
    _counters: tuple[str, ...] = field(
        default=(
            'n_methods_visited',
            'n_pruned_duplicates',
            'n_relocated_relativity',
            'n_blocked_relocations',
            'n_residual_non_terms',
        ),
        init=False,
        repr=False,
    )

    @property
    def changed(self) -> bool:
        """Whether the cleanup mutated the archive."""
        return bool(self.n_pruned_duplicates or self.n_relocated_relativity)

    def merge(self, other: 'LegacyCleanupStats') -> None:
        for counter in self._counters:
            setattr(self, counter, getattr(self, counter) + getattr(other, counter))

    def to_dict(self) -> dict[str, int]:
        return {counter: getattr(self, counter) for counter in self._counters}


def is_self_duplicate(
    parent: 'BaseModelMethod', contribution: 'BaseModelMethod'
) -> bool:
    """
    Whether `contribution` is an exact copy of `parent` (an artifact of recursive
    mapping-parser annotations in legacy archives), comparing serialized content with
    the nested `contributions` key stripped on both sides.
    """
    if contribution.m_def is not parent.m_def:
        return False
    # Reference quantities serialize as archive paths, so duplicates holding internal
    # references may compare unequal and are then retained (errs on the additive side).
    # The `m_def` key only appears on polymorphically nested sections; class identity
    # is already checked above.
    parent_dict = parent.m_to_dict()
    child_dict = contribution.m_to_dict()
    for key in ('contributions', 'm_def'):
        parent_dict.pop(key, None)
        child_dict.pop(key, None)
    return parent_dict == child_dict


def resolve_legacy_contributions(
    method: 'ModelMethod', logger: 'BoundLogger'
) -> LegacyCleanupStats:
    """
    Clean up legacy `contributions` content of a single `ModelMethod`: prune exact
    self-duplicates (recursive-mapping parser artifact), relocate `RelativityModel`
    entries to the typed `relativity` subsection, and warn about residual non-term
    entries.
    """
    from nomad_simulations.schema_packages.model_method import (
        HamiltonianTerm,
        RelativityModel,
    )

    stats = LegacyCleanupStats(n_methods_visited=1)
    if not method.contributions:
        return stats

    # `MSubSectionList.remove` is unsupported and `pop` shifts indices: iterate in reverse.
    for index in reversed(range(len(method.contributions))):
        if is_self_duplicate(method, method.contributions[index]):
            method.contributions.pop(index)
            stats.n_pruned_duplicates += 1
    if stats.n_pruned_duplicates:
        logger.warning(
            'Removed self-duplicate entries from `ModelMethod.contributions`'
            ' (recursive-mapping parser artifact).',
            n_removed=stats.n_pruned_duplicates,
        )

    relativity_def = type(method).m_def.all_sub_sections.get('relativity')
    for index in reversed(range(len(method.contributions))):
        contribution = method.contributions[index]
        if not isinstance(contribution, RelativityModel):
            continue
        if relativity_def is None or method.relativity is not None:
            stats.n_blocked_relocations += 1
            logger.warning(
                'Cannot relocate `RelativityModel` out of'
                ' `ModelMethod.contributions`: no free `relativity` subsection.',
            )
            continue
        method.contributions.pop(index)
        method.m_add_sub_section(relativity_def, contribution)
        stats.n_relocated_relativity += 1
        logger.warning(
            'Relocated `RelativityModel` from `ModelMethod.contributions` to the'
            ' typed `relativity` subsection.',
        )

    residual = [
        c.m_def.name for c in method.contributions if not isinstance(c, HamiltonianTerm)
    ]
    stats.n_residual_non_terms = len(residual)
    if residual:
        logger.warning(
            '`ModelMethod.contributions` holds sections that are not'
            ' `HamiltonianTerm`s; entries were left in place.',
            section_types=residual,
        )
    return stats


def cleanup_archive(
    archive: 'EntryArchive', logger: 'BoundLogger'
) -> LegacyCleanupStats:
    """
    Apply the legacy-`contributions` cleanup to every `ModelMethod` found anywhere in
    `archive`, and return the aggregated stats.
    """
    from nomad_simulations.schema_packages.model_method import ModelMethod

    stats = LegacyCleanupStats()
    # Materialize before mutating: the cleanup pops subsections during iteration.
    methods = [
        section
        for section in archive.m_all_contents()
        if isinstance(section, ModelMethod)
    ]
    for method in methods:
        # Skip methods detached from the archive because an ancestor was pruned as a
        # self-duplicate; re-cleaning them would only distort the stats.
        if method.m_root() is not archive:
            continue
        stats.merge(resolve_legacy_contributions(method, logger))
    return stats
