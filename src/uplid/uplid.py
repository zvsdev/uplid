"""Universal Prefixed Literal IDs - type-safe, human-readable identifiers."""

from __future__ import annotations

import re
from datetime import UTC
from datetime import datetime as dt_datetime
from typing import (
    TYPE_CHECKING,
    Any,
    LiteralString,
    Protocol,
    Self,
    get_args,
    get_origin,
    runtime_checkable,
)
from uuid import UUID, uuid7

from pydantic_core import CoreSchema, core_schema


if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable


# Base62 encoding: 0-9, A-Z, a-z (62 characters)
# IMPORTANT: '0' must be first character for zfill padding to work correctly
_BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_BASE62_DECODE_MAP = {c: i for i, c in enumerate(_BASE62_ALPHABET)}

# A 128-bit UUID requires ceiling(128 / log2(62)) = 22 base62 characters
_BASE62_UUID_LENGTH = 22

# UUIDv7 timestamp extraction (RFC 9562):
# Bits 0-47 contain 48-bit Unix timestamp in milliseconds
_UUIDV7_TIMESTAMP_SHIFT = 80  # 128 - 48 = shift to extract timestamp
_MS_PER_SECOND = 1000

# Prefix validation: snake_case (lowercase letters and single underscores)
# - Must start and end with a letter
# - Cannot have consecutive underscores
# - Single character prefixes are allowed
# - Maximum 64 characters to prevent DoS via regex on huge inputs
_PREFIX_PATTERN = re.compile(r"^[a-z]([a-z]*(_[a-z]+)*)?$")
_PREFIX_MAX_LENGTH = 64


class UPLIDError(ValueError):
    """Raised when UPLID parsing or validation fails."""


@runtime_checkable
class UPLIDType(Protocol):
    """Protocol for any UPLID, useful for generic function signatures.

    Example:
        def log_entity(entity_id: UPLIDType) -> None:
            print(f"{entity_id.prefix} created at {entity_id.datetime}")
    """

    __slots__ = ()

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

    @property
    def timestamp(self) -> float:
        """The Unix timestamp (seconds) from the UUIDv7."""
        ...

    @property
    def base62_uid(self) -> str:
        """The base62-encoded UID (22 characters)."""
        ...

    def __str__(self) -> str:
        """String representation as '<prefix>_<base62uid>'."""
        ...


def _int_to_base62(num: int) -> str:
    """Convert integer to base62 string, padded to 22 chars for UUIDv7."""
    if num == 0:
        return "0" * _BASE62_UUID_LENGTH

    result: list[str] = []
    while num > 0:
        num, remainder = divmod(num, 62)
        result.append(_BASE62_ALPHABET[remainder])

    return "".join(reversed(result)).zfill(_BASE62_UUID_LENGTH)


def _base62_to_int(s: str) -> int:
    """Convert base62 string to integer.

    Raises:
        ValueError: If input exceeds expected UUID length.
        KeyError: If input contains invalid base62 characters.
    """
    if len(s) > _BASE62_UUID_LENGTH:
        raise ValueError(f"Input exceeds maximum length of {_BASE62_UUID_LENGTH}")
    result = 0
    for char in s:
        result = result * 62 + _BASE62_DECODE_MAP[char]
    return result


def _validate_prefix(prefix: str) -> None:
    """Validate that prefix follows snake_case rules.

    Raises:
        UPLIDError: If prefix is invalid.
    """
    if len(prefix) > _PREFIX_MAX_LENGTH:
        raise UPLIDError(
            f"Prefix must be at most {_PREFIX_MAX_LENGTH} characters, got {len(prefix)}"
        )
    if not _PREFIX_PATTERN.match(prefix):
        raise UPLIDError(
            f"Prefix must be snake_case (lowercase letters, single underscores, "
            f"cannot start/end with underscore or have consecutive underscores), "
            f"got {prefix!r}"
        )


class UPLID[PREFIX: LiteralString]:
    """Universal Prefixed Literal ID with type-safe prefix validation.

    A UPLID combines a string prefix (like 'usr', 'api_key') with a UUIDv7,
    encoded in base62 for compactness. The prefix enables runtime and static
    type checking to prevent mixing IDs from different domains.

    Example:
        >>> from typing import Literal
        >>> UserId = UPLID[Literal["usr"]]
        >>> user_id = UPLID.generate("usr")
        >>> print(user_id)  # usr_1a2B3c4D5e6F7g8H9i0J1k

    Note:
        The `datetime` and `timestamp` properties assume the underlying UUID
        is a valid UUIDv7. If you construct a UPLID with a non-UUIDv7 UUID
        (e.g., UUIDv4), these properties will return meaningless values.
    """

    __slots__ = ("_base62_uid", "_prefix", "_uid")

    def __init__(self, prefix: PREFIX, uid: UUID) -> None:
        """Initialize a UPLID with a prefix and UUID.

        Args:
            prefix: The string prefix (must be snake_case).
            uid: The UUID (should be UUIDv7 for datetime/timestamp to be meaningful).

        Raises:
            UPLIDError: If prefix is not valid snake_case.
        """
        _validate_prefix(prefix)
        self._prefix = prefix
        self._uid = uid
        self._base62_uid: str | None = None

    @property
    def prefix(self) -> PREFIX:
        """The prefix identifier (e.g., 'usr', 'api_key')."""
        return self._prefix

    @property
    def uid(self) -> UUID:
        """The underlying UUID (typically UUIDv7)."""
        return self._uid

    @property
    def base62_uid(self) -> str:
        """The base62-encoded UID (22 characters)."""
        if self._base62_uid is None:
            self._base62_uid = _int_to_base62(self._uid.int)
        return self._base62_uid

    @property
    def datetime(self) -> dt_datetime:
        """The timestamp extracted from the UUIDv7.

        Note:
            This assumes the UUID is a valid UUIDv7. For non-UUIDv7 UUIDs,
            the returned datetime will be meaningless.
        """
        ms = self._uid.int >> _UUIDV7_TIMESTAMP_SHIFT
        return dt_datetime.fromtimestamp(ms / _MS_PER_SECOND, tz=UTC)

    @property
    def timestamp(self) -> float:
        """The Unix timestamp (seconds) from the UUIDv7.

        Note:
            This assumes the UUID is a valid UUIDv7. For non-UUIDv7 UUIDs,
            the returned timestamp will be meaningless.
        """
        ms = self._uid.int >> _UUIDV7_TIMESTAMP_SHIFT
        return ms / _MS_PER_SECOND

    def __str__(self) -> str:
        """Return the string representation as '<prefix>_<base62uid>'."""
        return f"{self._prefix}_{self.base62_uid}"

    def __repr__(self) -> str:
        """Return a detailed representation."""
        return f"UPLID({self._prefix!r}, {self.base62_uid!r})"

    def __hash__(self) -> int:
        """Return hash for use in sets and dict keys."""
        return hash((self._prefix, self._uid))

    def __eq__(self, other: object) -> bool:
        """Check equality with another UPLID."""
        if isinstance(other, UPLID):
            return self._prefix == other._prefix and self._uid == other._uid
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self._prefix, self._uid) < (other._prefix, other._uid)  # type: ignore[operator]
        return NotImplemented

    def __le__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self._prefix, self._uid) <= (other._prefix, other._uid)  # type: ignore[operator]
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self._prefix, self._uid) > (other._prefix, other._uid)  # type: ignore[operator]
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self._prefix, self._uid) >= (other._prefix, other._uid)  # type: ignore[operator]
        return NotImplemented

    def __copy__(self) -> Self:
        """Return self (UPLIDs are immutable)."""
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        """Return self (UPLIDs are immutable)."""
        return self

    def __reduce__(self) -> tuple[type[Self], tuple[str, UUID]]:
        """Support pickling for multiprocessing, caching, etc."""
        return (type(self), (self._prefix, self._uid))

    @classmethod
    def generate(cls, prefix: PREFIX) -> Self:
        """Generate a new UPLID with the given prefix.

        Args:
            prefix: The string prefix (must be snake_case: lowercase letters
                and single underscores, cannot start/end with underscore).

        Returns:
            A new UPLID instance.

        Raises:
            UPLIDError: If the prefix is not valid snake_case.
        """
        _validate_prefix(prefix)
        instance = cls.__new__(cls)
        instance._prefix = prefix  # noqa: SLF001
        instance._uid = uuid7()  # noqa: SLF001
        instance._base62_uid = None  # noqa: SLF001
        return instance

    @classmethod
    def from_string(cls, string: str, prefix: PREFIX) -> Self:
        """Parse a UPLID from its string representation.

        Args:
            string: The string to parse (format: '<prefix>_<base62uid>').
            prefix: The expected prefix.

        Returns:
            A UPLID instance.

        Raises:
            UPLIDError: If the string format is invalid or prefix doesn't match.

        Note:
            This method does not validate that the decoded UUID is a valid
            UUIDv7. The datetime/timestamp properties may return meaningless
            values if the original ID was not created with a UUIDv7.
        """
        if "_" not in string:
            raise UPLIDError(f"UPLID must be in format '<prefix>_<uid>', got {string!r}")

        last_underscore = string.rfind("_")
        parsed_prefix = string[:last_underscore]
        encoded_uid = string[last_underscore + 1 :]

        _validate_prefix(parsed_prefix)

        if parsed_prefix != prefix:
            raise UPLIDError(f"Expected prefix {prefix!r}, got {parsed_prefix!r}")

        if len(encoded_uid) != _BASE62_UUID_LENGTH:
            raise UPLIDError(
                f"UID must be {_BASE62_UUID_LENGTH} characters, got {len(encoded_uid)}"
            )

        try:
            uid_int = _base62_to_int(encoded_uid)
            uid = UUID(int=uid_int)
        except (KeyError, ValueError) as e:
            raise UPLIDError(f"Invalid base62 UID: {encoded_uid!r}") from e

        instance = cls.__new__(cls)
        instance._prefix = prefix  # noqa: SLF001
        instance._uid = uid  # noqa: SLF001
        instance._base62_uid = encoded_uid  # noqa: SLF001
        return instance

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,  # noqa: ANN401
        handler: Any,  # noqa: ANN401
    ) -> CoreSchema:
        """Pydantic integration for validation and serialization.

        Note:
            This method accesses typing internals (__args__, __value__) which
            may change between Python versions. Integration tests should verify
            compatibility with supported Python versions.
        """
        origin = get_origin(source_type)
        if origin is None:
            raise UPLIDError(
                "UPLID must be parameterized with a prefix literal, e.g. UPLID[Literal['usr']]"
            )

        args = get_args(source_type)
        if not args:  # pragma: no cover
            raise UPLIDError("UPLID requires a Literal prefix type argument")

        prefix_type = args[0]
        prefix_args = get_args(prefix_type)

        # Handle TypeVar case (Python 3.12+ type parameter syntax)
        if not prefix_args:  # pragma: no cover
            if hasattr(prefix_type, "__value__"):
                prefix_args = get_args(prefix_type.__value__)
            if not prefix_args:
                raise UPLIDError(f"Could not extract prefix from {prefix_type}")

        prefix_str: str = prefix_args[0]

        def validate(v: UPLID[Any] | str) -> UPLID[Any]:
            if isinstance(v, str):
                return cls.from_string(v, prefix_str)
            if isinstance(v, UPLID):
                if v.prefix != prefix_str:
                    raise UPLIDError(f"Expected prefix {prefix_str!r}, got {v.prefix!r}")
                return v
            raise UPLIDError(f"Expected UPLID or str, got {type(v).__name__}")

        return core_schema.json_or_python_schema(
            json_schema=core_schema.chain_schema(
                [
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(validate),
                ]
            ),
            python_schema=core_schema.no_info_plain_validator_function(validate),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )


def _get_prefix[PREFIX: LiteralString](uplid_type: type[UPLID[PREFIX]]) -> str:
    """Extract the prefix string from a parameterized UPLID type."""
    args = get_args(uplid_type)
    if not args:
        raise UPLIDError("UPLID type must be parameterized with a Literal prefix")
    literal_type = args[0]
    literal_args = get_args(literal_type)
    # Handle TypeVar case (Python 3.12+ type parameter syntax)
    if not literal_args and hasattr(literal_type, "__value__"):  # pragma: no cover
        literal_args = get_args(literal_type.__value__)
    if not literal_args:  # pragma: no cover
        raise UPLIDError(f"Could not extract prefix from {literal_type}")
    return literal_args[0]


def factory[PREFIX: LiteralString](
    uplid_type: type[UPLID[PREFIX]],
) -> Callable[[], UPLID[PREFIX]]:
    """Create a factory function for generating new UPLIDs of a specific type.

    This is useful with Pydantic's Field(default_factory=...).

    Example:
        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))
    """
    prefix = _get_prefix(uplid_type)

    def _factory() -> UPLID[PREFIX]:
        return UPLID.generate(prefix)

    return _factory


def parse[PREFIX: LiteralString](
    uplid_type: type[UPLID[PREFIX]],
) -> Callable[[str], UPLID[PREFIX]]:
    """Create a parse function for converting strings to UPLIDs.

    This is useful for parsing user input outside of Pydantic models.
    Raises UPLIDError on invalid input.

    Example:
        UserId = UPLID[Literal["usr"]]
        parse_user_id = parse(UserId)

        try:
            user_id = parse_user_id("usr_1a2B3c4D5e6F7g8H9i0J1k")
        except UPLIDError as e:
            print(f"Invalid ID: {e}")
    """
    prefix = _get_prefix(uplid_type)

    def _parse(v: str) -> UPLID[PREFIX]:
        return UPLID.from_string(v, prefix)

    return _parse
