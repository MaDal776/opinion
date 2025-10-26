"""Utilities for normalizing Opinion SDK responses."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Iterable, List


_PRIMITIVE_TYPES = (str, int, float, bool)


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, _PRIMITIVE_TYPES):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return _normalize(value.value)
    if isinstance(value, dict):
        return {key: _normalize(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize(item) for item in value]
    if is_dataclass(value):
        return _normalize(asdict(value))
    if hasattr(value, "dict") and callable(value.dict):
        return _normalize(value.dict())  # type: ignore[no-any-return]
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return _normalize(value.model_dump())
    if hasattr(value, "__dict__"):
        data = {
            key: val
            for key, val in value.__dict__.items()
            if not key.startswith("_")
        }
        if data:
            return _normalize(data)
    return value


def extract_list(response: Any) -> List[Dict[str, Any]]:
    if response.errno != 0:
        raise RuntimeError(response.errmsg or "Opinion API error")
    result = getattr(response, "result", None) or {}
    payload = getattr(result, "list", None)
    if payload is None:
        payload = getattr(result, "data", None)
    if payload is None and result:
        payload = result
    if payload is None:
        return []
    normalized = _normalize(payload)
    if isinstance(normalized, list):
        return [item if isinstance(item, dict) else {"value": item} for item in normalized]
    if isinstance(normalized, dict):
        return [normalized]
    return [{"value": normalized}]


def extract_data(response: Any) -> Dict[str, Any]:
    if response.errno != 0:
        raise RuntimeError(response.errmsg or "Opinion API error")
    result = getattr(response, "result", None) or {}
    payload = getattr(result, "data", None)
    if payload is None and result:
        payload = result
    if payload is None:
        return {}
    normalized = _normalize(payload)
    if isinstance(normalized, dict):
        return normalized
    if isinstance(normalized, list):
        return {"items": normalized}
    return {"value": normalized}


def normalize(value: Any) -> Any:
    """Public helper for ad-hoc normalization needs."""
    return _normalize(value)
