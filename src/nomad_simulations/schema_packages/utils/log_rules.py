"""
Declarative log rules for `normalize` methods.

A log rule states that a section in a given state should emit a log record. The rule is
attached to `normalize` with the `log_when` decorator, which evaluates it after the
decorated `normalize` has run and logs through the `logger` passed to `normalize`. Rules
only read the section: they never set, change or unset a quantity.

Every rule is also registered on the decorated function, so a single generated test can
collect all rules of the package, build section states from the quantities each rule
depends on, and check that the rule fires exactly in the matching states while leaving
every quantity as it was.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

LOG_LEVELS = ('debug', 'info', 'warning', 'error', 'critical')


@dataclass(frozen=True)
class LogRule:
    """
    A state of a section that should elicit a log record.

    Attributes:
        level: Log level of the record, one of `LOG_LEVELS`.
        on: Names of the quantities the condition reads. They are attached to the record
            as key-value context and define the states the generated test enumerates.
        condition: Predicate on the section; the record is emitted when it returns `True`.
        message: Event text of the record. Values are passed as context, not formatted in.
        samples: Values to try per quantity in the generated test, for quantities whose
            values cannot be enumerated from their type (free strings, arrays).
    """

    level: str
    on: tuple[str, ...]
    condition: Callable[[Any], bool]
    message: str
    samples: dict[str, list[Any]] = field(default_factory=dict)


def log_when(
    level: str,
    on: tuple[str, ...],
    condition: Callable[[Any], bool],
    message: str,
    samples: dict[str, list[Any]] | None = None,
) -> Callable:
    """
    Decorate a `normalize` method with a log rule.

    After the decorated `normalize` has run, `condition(self)` is evaluated and, if it
    holds, `message` is logged at `level` with the values of the quantities in `on` as
    context. Decorators stack; each adds one rule.

    Args:
        level: Log level, one of `LOG_LEVELS`.
        on: Names of the quantities the condition reads.
        condition: Predicate on the section.
        message: Event text of the log record.
        samples: Values to try per quantity in the generated test (see `LogRule`).
    """
    if level not in LOG_LEVELS:
        raise ValueError(f'Unknown log level {level!r}; expected one of {LOG_LEVELS}.')
    rule = LogRule(
        level=level,
        on=tuple(on),
        condition=condition,
        message=message,
        samples=samples or {},
    )

    def decorator(normalize: Callable) -> Callable:
        @functools.wraps(normalize)
        def wrapper(
            self, archive: EntryArchive, logger: BoundLogger, *args, **kwargs
        ) -> Any:
            result = normalize(self, archive, logger, *args, **kwargs)
            if rule.condition(self):
                quantities = self.m_def.all_quantities
                context = {name: self.m_get(quantities[name]) for name in rule.on}
                getattr(logger, rule.level)(rule.message, **context)
            return result

        wrapper.log_rules = (*getattr(normalize, 'log_rules', ()), rule)  # type: ignore[attr-defined]
        return wrapper

    return decorator
