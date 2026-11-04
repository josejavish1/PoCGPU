"""Pure Domain Exceptions for Universal Hybrid FinOps Advisor."""

from __future__ import annotations

from decimal import Decimal
from types import MappingProxyType
from typing import Mapping, Union


class DomainException(Exception):
    """Base exception for all domain-level errors."""
    pass


class DomainLookupError(DomainException):
    """Raised when a hardware SKU, model profile, or pricing spec is absent from the catalog."""
    pass


class ConstitutionalGateViolationError(DomainException):
    """Raised when an infrastructure or financial configuration violates physical or actuarial invariants."""

    def __init__(
        self,
        rule_code: str,
        i18n_key: str,
        i18n_params: Mapping[str, Union[str, int, Decimal]],
    ) -> None:
        self.rule_code = rule_code
        self.i18n_key = i18n_key
        self.i18n_params: Mapping[str, Union[str, int, Decimal]] = MappingProxyType(dict(i18n_params))
        super().__init__(f"[{rule_code}] {i18n_key} | Params: {dict(self.i18n_params)}")
