import importlib
import itertools
import pkgutil

import numpy as np
import pytest
from nomad.datamodel import EntryArchive
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import MEnum, Quantity
from nomad.metainfo.data_type import Enum, ExactNumber, InexactNumber, m_bool
from structlog.testing import CapturingLogger

import nomad_simulations.schema_packages
from nomad_simulations.schema_packages.utils.log_rules import LogRule, log_when

UNSET = object()


class Sample(ArchiveSection):
    kind = Quantity(type=MEnum('a', 'b'))
    width = Quantity(type=float)

    @log_when(
        'warning',
        on=('kind', 'width'),
        condition=lambda self: self.kind == 'a' and self.width is not None,
        message='Width is set for kind a.',
    )
    @log_when(
        'info',
        on=('kind',),
        condition=lambda self: self.kind is None,
        message='No kind.',
    )
    def normalize(self, archive, logger):
        super().normalize(archive, logger)


@pytest.mark.parametrize(
    ('kind', 'width', 'expected_calls'),
    [
        (
            'a',
            0.5,
            [('warning', 'Width is set for kind a.', {'kind': 'a', 'width': 0.5})],
        ),
        ('a', None, []),
        ('b', 0.5, []),
        (None, 0.5, [('info', 'No kind.', {'kind': None})]),
        (None, None, [('info', 'No kind.', {'kind': None})]),
    ],
    ids=['matching-state', 'condition-false', 'other-kind', 'second-rule', 'empty'],
)
def test_log_when_logs_matching_state_with_context(kind, width, expected_calls):
    sample = Sample(kind=kind, width=width)
    logger = CapturingLogger()

    sample.normalize(EntryArchive(), logger)

    assert sorted(
        (call.method_name, call.args[0], call.kwargs) for call in logger.calls
    ) == sorted(expected_calls)


def test_log_when_registers_stacked_rules():
    assert [rule.message for rule in Sample.normalize.log_rules] == [
        'No kind.',
        'Width is set for kind a.',
    ]


def test_log_when_rejects_unknown_level():
    with pytest.raises(ValueError, match='Unknown log level'):
        log_when('warn', on=('kind',), condition=bool, message='')


def collect_log_rules() -> list[tuple[type[ArchiveSection], LogRule]]:
    """
    Import every module of `nomad_simulations.schema_packages` and return each section
    class whose own `normalize` carries log rules, paired with each of its rules.
    """
    package = nomad_simulations.schema_packages
    for module in pkgutil.walk_packages(package.__path__, f'{package.__name__}.'):
        importlib.import_module(module.name)

    def subclasses(cls: type[ArchiveSection]) -> set[type[ArchiveSection]]:
        direct = set(cls.__subclasses__())
        return direct.union(*(subclasses(sub) for sub in direct))

    return sorted(
        (
            (cls, rule)
            for cls in subclasses(ArchiveSection)
            if cls.__module__.startswith(package.__name__)
            for rule in getattr(cls.__dict__.get('normalize'), 'log_rules', ())
        ),
        key=lambda pair: (pair[0].__name__, pair[1].message),
    )


def candidate_values(cls: type[ArchiveSection], rule: LogRule, name: str) -> list:
    """
    Values to try for one quantity: the rule's samples, else values enumerated from the
    quantity type. Always includes `UNSET`.
    """
    quantity = cls.m_def.all_quantities.get(name)
    assert quantity is not None, f'{cls.__name__} has no quantity {name!r}'
    if name in rule.samples:
        return [*rule.samples[name], UNSET]
    assert not quantity.shape, (
        f'{cls.__name__}.{name} is not scalar; give `samples` in the rule'
    )
    if isinstance(quantity.type, Enum):
        return [*quantity.type._list, UNSET]
    if isinstance(quantity.type, m_bool):
        return [True, False, UNSET]
    if isinstance(quantity.type, ExactNumber):
        return [-1, 0, 1, UNSET]
    if isinstance(quantity.type, InexactNumber):
        return [-1.0, 0.0, 0.5, 1.0, UNSET]
    raise AssertionError(
        f'Cannot enumerate values of {cls.__name__}.{name}; give `samples` in the rule'
    )


def generate_states() -> list:
    params = []
    for cls, rule in collect_log_rules():
        values = [candidate_values(cls, rule, name) for name in rule.on]
        for combination in itertools.product(*values):
            state = {
                name: value
                for name, value in zip(rule.on, combination)
                if value is not UNSET
            }
            label = ','.join(
                f'{name}={"unset" if value is UNSET else value}'
                for name, value in zip(rule.on, combination)
            )
            params.append(pytest.param(cls, rule, state, id=f'{cls.__name__}[{label}]'))
    return params


def same_value(before, after) -> bool:
    if hasattr(before, 'units'):
        return before.units == after.units and np.array_equal(
            before.magnitude, after.magnitude
        )
    return np.array_equal(before, after)


@pytest.mark.parametrize(('cls', 'rule', 'state'), generate_states())
def test_log_rule_fires_exactly_on_matching_state(cls, rule, state):
    """
    For every log rule in the package and every state built from its quantities, the
    rule's level is logged by that rule exactly when the condition holds, and
    `normalize` leaves every set quantity with the value it had before.
    """
    section = cls(**state)
    quantities = section.m_def.all_quantities
    before = {
        name: section.m_get(quantity)
        for name, quantity in quantities.items()
        if section.m_is_set(quantity)
    }
    logger = CapturingLogger()

    section.normalize(EntryArchive(), logger)

    after = {
        name: section.m_get(quantities[name])
        for name in before
        if section.m_is_set(quantities[name])
    }
    assert after.keys() == before.keys()
    assert all(same_value(before[name], after[name]) for name in before)
    rule_levels = [
        call.method_name for call in logger.calls if call.args[:1] == (rule.message,)
    ]
    assert rule_levels == ([rule.level] if rule.condition(section) else [])
