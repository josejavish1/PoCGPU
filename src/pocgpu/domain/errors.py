"""Stable technical errors and structured domain issues."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

type IssueParameter = str | int | bool | None


class IssueKind(StrEnum):
    """State-relevant issue categories with deterministic precedence."""

    INVALID = "INVALID"
    STALE = "STALE"
    INPUT_REQUIRED = "INPUT_REQUIRED"
    POLICY_REQUIRED = "POLICY_REQUIRED"
    BENCHMARK_REQUIRED = "BENCHMARK_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


class IssueSeverity(StrEnum):
    """Technical issue impact independent from presentation language."""

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class DomainValidationError(ValueError):
    """Fail-closed domain validation error identified by a stable code."""

    def __init__(
        self,
        code: str,
        path: tuple[str, ...] = (),
        parameters: tuple[tuple[str, IssueParameter], ...] = (),
    ) -> None:
        self.code = code
        self.path = path
        self.parameters = parameters
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class DomainIssue:
    """Structured issue suitable for localization at an interface boundary."""

    code: str
    kind: IssueKind
    severity: IssueSeverity
    path: tuple[str, ...]
    parameters: tuple[tuple[str, IssueParameter], ...]
    localization_key: str

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", self.code) is None:
            raise DomainValidationError("INVALID_ISSUE_CODE", ("code",))
        if not self.localization_key or not self.localization_key.isascii():
            raise DomainValidationError("INVALID_LOCALIZATION_KEY", ("localization_key",))
        parameter_names = tuple(name for name, _ in self.parameters)
        if len(parameter_names) != len(set(parameter_names)):
            raise DomainValidationError("DUPLICATE_ISSUE_PARAMETER", ("parameters",))
