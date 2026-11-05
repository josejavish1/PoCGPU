"""Versioned canonical JSON serialization and content identity."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pocgpu.domain.identifiers import (
    ContentHash,
    CurrencyCode,
    OpaqueId,
    RecordRevision,
    SchemaId,
    SemanticVersion,
)
from pocgpu.domain.numeric import canonical_decimal
from pocgpu.domain.time import UtcInstant


def _canonical_timestamp(instant: UtcInstant) -> str:
    text = instant.value.isoformat(timespec="microseconds").replace("+00:00", "Z")
    prefix, remainder = text.split(".", 1)
    fraction = remainder.removesuffix("Z").rstrip("0")
    return f"{prefix}.{fraction}Z" if fraction else f"{prefix}Z"


def _canonicalize(value: Any) -> Any:
    if value is None or type(value) in {bool, int}:
        return value
    if type(value) is float:
        raise TypeError("FLOAT_PROHIBITED")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Decimal):
        return canonical_decimal(value)
    if isinstance(value, OpaqueId):
        return value.value
    if isinstance(value, (SemanticVersion, CurrencyCode, ContentHash)):
        return value.value
    if isinstance(value, RecordRevision):
        return value.value
    if isinstance(value, UtcInstant):
        return _canonical_timestamp(value)
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, datetime):
        raise TypeError("RAW_DATETIME_PROHIBITED")
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonicalize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("CANONICAL_KEY_MUST_BE_STRING")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise TypeError("DUPLICATE_NORMALIZED_KEY")
            normalized[normalized_key] = _canonicalize(item)
        return normalized
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        normalized_values = [_canonicalize(item) for item in value]
        return sorted(
            normalized_values,
            key=lambda item: json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
        )
    raise TypeError(f"UNSUPPORTED_CANONICAL_TYPE:{type(value).__name__}")


def canonical_json_bytes(
    value: Any,
    schema_id: SchemaId,
    schema_version: SemanticVersion,
) -> bytes:
    """Serialize a value under an explicit canonical schema envelope."""

    envelope = {
        "payload": _canonicalize(value),
        "schema_id": schema_id.value,
        "schema_version": schema_version.value,
    }
    return json.dumps(
        envelope,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def content_hash(canonical_bytes: bytes) -> ContentHash:
    """Calculate lowercase SHA-256 identity for canonical bytes."""

    if not isinstance(canonical_bytes, bytes):
        raise TypeError("CANONICAL_BYTES_REQUIRED")
    return ContentHash(hashlib.sha256(canonical_bytes).hexdigest())
