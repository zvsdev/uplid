"""Universal Prefixed Literal IDs - type-safe, human-readable identifiers."""

from __future__ import annotations

import os
import re
from datetime import UTC
from datetime import datetime as dt_datetime
from typing import TYPE_CHECKING, LiteralString, Protocol, Self, runtime_checkable
from uuid import UUID, uuid7


if TYPE_CHECKING:
    import datetime as dt


PREFIX_PATTERN = re.compile(r"^[a-z]([a-z_]*[a-z])?$")


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


class UPLID[PREFIX: LiteralString]:
    """Universal Prefixed Literal ID with type-safe prefix validation.

    A UPLID combines a string prefix (like 'usr', 'api_key') with a UUIDv7,
    encoded in base62 for compactness. The prefix enables runtime and static
    type checking to prevent mixing IDs from different domains.

    Example:
        >>> UserId = UPLID[Literal["usr"]]
        >>> user_id = UPLID.generate("usr")
        >>> print(user_id)  # usr_4mJ9k2L8nP3qR7sT1vW5xY
    """

    __slots__ = ("_base62_uid", "prefix", "uid")

    prefix: PREFIX
    uid: UUID
    _base62_uid: str | None

    def __init__(self, prefix: PREFIX, uid: UUID) -> None:
        """Initialize a UPLID with a prefix and UUID."""
        self.prefix = prefix
        self.uid = uid
        self._base62_uid = None

    @property
    def base62_uid(self) -> str:
        """The base62-encoded UID (22 characters)."""
        if self._base62_uid is None:
            self._base62_uid = _int_to_base62(self.uid.int)
        return self._base62_uid

    @property
    def datetime(self) -> dt_datetime:
        """The timestamp extracted from the UUIDv7."""
        ms = self.uid.int >> 80
        return dt_datetime.fromtimestamp(ms / 1000, tz=UTC)

    @property
    def timestamp(self) -> float:
        """The Unix timestamp (seconds) from the UUIDv7."""
        ms = self.uid.int >> 80
        return ms / 1000

    def __str__(self) -> str:
        """Return the string representation as '<prefix>_<base62uid>'."""
        return f"{self.prefix}_{self.base62_uid}"

    def __repr__(self) -> str:
        """Return a detailed representation."""
        return f"UPLID({self.prefix!r}, {self.base62_uid!r})"

    def __hash__(self) -> int:
        """Return hash for use in sets and dict keys."""
        return hash((self.prefix, self.uid))

    def __eq__(self, other: object) -> bool:
        """Check equality with another UPLID."""
        if isinstance(other, UPLID):
            return self.prefix == other.prefix and self.uid == other.uid
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) < (other.prefix, other.uid)
        return NotImplemented

    def __le__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) <= (other.prefix, other.uid)
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) > (other.prefix, other.uid)
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) >= (other.prefix, other.uid)
        return NotImplemented

    @classmethod
    def generate(cls, prefix: PREFIX, at: dt_datetime | None = None) -> Self:
        """Generate a new UPLID with the given prefix."""
        if not PREFIX_PATTERN.match(prefix):
            raise UPLIDError(
                f"Prefix must be snake_case (lowercase letters, underscores, "
                f"cannot start/end with underscore), got {prefix!r}"
            )

        if at is not None:
            ms = int(at.timestamp() * 1000)
            rand_bits = int.from_bytes(os.urandom(10), "big")
            uuid_int = (ms << 80) | (0x7 << 76) | (rand_bits & ((1 << 76) - 1))
            uuid_int = (uuid_int & ~(0x3 << 62)) | (0x2 << 62)
            uid = UUID(int=uuid_int)
        else:
            uid = uuid7()

        return cls(prefix, uid)

    @classmethod
    def from_string(cls, string: str, prefix: PREFIX) -> Self:
        """Parse a UPLID from its string representation."""
        if "_" not in string:
            raise UPLIDError(f"UPLID must be in format '<prefix>_<uid>', got {string!r}")

        last_underscore = string.rfind("_")
        parsed_prefix = string[:last_underscore]
        encoded_uid = string[last_underscore + 1 :]

        if not PREFIX_PATTERN.match(parsed_prefix):
            raise UPLIDError(f"Prefix must be snake_case, got {parsed_prefix!r}")

        if parsed_prefix != prefix:
            raise UPLIDError(f"Expected prefix {prefix!r}, got {parsed_prefix!r}")

        if len(encoded_uid) != 22:
            raise UPLIDError(f"UID must be 22 characters, got {len(encoded_uid)}")

        try:
            uid_int = _base62_to_int(encoded_uid)
            uid = UUID(int=uid_int)
        except (KeyError, ValueError) as e:
            raise UPLIDError(f"Invalid base62 UID: {encoded_uid!r}") from e

        instance = cls(prefix, uid)
        instance._base62_uid = encoded_uid
        return instance
