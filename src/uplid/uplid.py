"""Universal Prefixed Literal IDs - type-safe, human-readable identifiers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable


if TYPE_CHECKING:
    import datetime as dt
    from uuid import UUID


class UPLIDError(ValueError):
    """Raised when UPLID parsing or validation fails."""


@runtime_checkable
class UPLIDType(Protocol):
    """Protocol for any UPLID, useful for generic function signatures."""

    @property
    def prefix(self) -> str:
        """The prefix identifier (e.g., 'usr', 'api_key')."""
        ...

    @property
    def uid(self) -> UUID:
        """The underlying UUIDv7."""
        ...

    @property
    def datetime(self) -> dt.datetime:
        """The timestamp extracted from the UUIDv7."""
        ...

    def __str__(self) -> str:
        """String representation as '<prefix>_<base62uid>'."""
        ...


_BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_BASE62_MAP = {c: i for i, c in enumerate(_BASE62)}


def _int_to_base62(num: int) -> str:
    """Convert integer to base62 string, padded to 22 chars for UUIDv7."""
    if num == 0:
        return "0" * 22

    result: list[str] = []
    while num > 0:
        num, remainder = divmod(num, 62)
        result.append(_BASE62[remainder])

    return "".join(reversed(result)).zfill(22)


def _base62_to_int(s: str) -> int:
    """Convert base62 string to integer."""
    result = 0
    for char in s:
        result = result * 62 + _BASE62_MAP[char]
    return result
