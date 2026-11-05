"""Captured-time port."""

from __future__ import annotations

from typing import Protocol

from pocgpu.domain.time import UtcInstant


class Clock(Protocol):
    """Provide an explicitly captured current instant."""

    def now(self) -> UtcInstant: ...
