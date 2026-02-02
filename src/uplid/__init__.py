"""Universal Prefixed Literal IDs - type-safe, human-readable identifiers."""

from __future__ import annotations

from uplid.uplid import UPLID, UPLIDError, UPLIDType, _get_prefix, factory, parse


__all__ = ["UPLID", "UPLIDError", "UPLIDType", "_get_prefix", "factory", "parse"]
