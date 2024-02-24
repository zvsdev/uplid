from typing import Any, Callable, LiteralString, Self, Type, get_args, get_origin

from base62 import decode, encode
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
from ulid import ULID


class PrefixedId[PREFIX: LiteralString]:
    """
    A class representing an ID with a prefixed str identifier. The UID portion is managed using ULID (Universall
    Unique Lexicographically Sortable Identifier) format encoded via base62.

    Attributes:
        prefix (PREFIX): A string literal prefix for the ID. Can be specified as a type param or infered from args
        uid (ULID): The ULID object representing the unique identifier.
        encoded_uid (str): The encoded string representation of the ULID.

    Methods:
        from_string(string: str, prefix: PREFIX): Class method to create an instance of PrefixedId from a
            string representation.
        generate(prefix: PREFIX): Class method to generate a new PrefixedId with a given prefix.
        factory(prefix: PREFIX): Class method to return a callable that generates new PrefixedIds with the given prefix.

    Raises:
        ValueError: If the string representation does not conform to the expected format, if prefix
            contains non-alphabetic characters, is not lowercase, or does not match the expected prefix.

    Note:
        This class requires a literal string as a type parameter for PREFIX. It integrates with Pydantic
        for validation and serialization purposes.
    """

    prefix: PREFIX
    uid: ULID
    encoded_uid: str

    def __init__(self, prefix: PREFIX, uid: ULID | str) -> None:
        self.prefix = prefix
        if isinstance(uid, ULID):
            self.uid = uid
            self.encoded_uid = encode(int(uid))
        else:
            self.uid = ULID.from_int(decode(uid))
            self.encoded_uid = uid

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"{self.prefix}_{self.encoded_uid}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.prefix == other.prefix and self.uid == other.uid
        return False

    @classmethod
    def from_string(cls, string: str, prefix: PREFIX) -> Self:
        split_content = string.split("_")
        if len(split_content) != 2:
            raise ValueError(
                f"Prefixed Id Strings must be of the form <prefix>_<uid>, received {string}"
            )
        _prefix, encoded_uid = split_content
        if not _prefix.isalpha():
            raise ValueError(f"Prefix can only contain alphabetic characters, got {_prefix}")
        if not _prefix.islower():
            raise ValueError(f"Prefix must be lowercase, got {_prefix}")
        if _prefix != prefix:
            raise ValueError(f"Expected prefix to be {prefix}, got {_prefix}")
        if not encoded_uid:
            raise ValueError("Expected encoded_uid to be a non-empty string")
        if len(encoded_uid) != 21:
            raise ValueError(
                f"Expected encoded_uid to be 26 characters long, got {len(encoded_uid)}"
            )
        _uid = ULID.from_int(decode(encoded_uid))
        return cls(prefix, _uid)

    @classmethod
    def generate(cls, prefix: PREFIX) -> Self:
        return cls(prefix, ULID())

    @classmethod
    def factory(cls, prefix: PREFIX) -> Callable[[], Self]:
        def f() -> Self:
            return cls.generate(prefix)

        return f

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        origin: Type[cls] | None = get_origin(source_type)
        if origin is None:  # used as `x: PrefixId` without params
            raise RuntimeError("PrefixId must be used with a prefix literal string")
        prefix_str_type = get_args(source_type)[0]
        type_args = get_args(prefix_str_type)
        if not type_args:  # When prefix is a TypeVar
            prefix_str_type = prefix_str_type.__value__
            prefix_str = prefix_str_type.__args__[0]
        else:
            prefix_str = type_args[0]

        if not prefix_str:
            raise RuntimeError(f"Expected prefix to be a literal string, got {prefix_str_type}")

        def val_str(v: str) -> PrefixedId[PREFIX]:
            try:
                prefixed_id = cls.from_string(v, prefix_str)
            except ValueError as e:
                raise AssertionError(e) from e
            return prefixed_id

        def val_prefix(v: PrefixedId[PREFIX] | str) -> PrefixedId[PREFIX]:
            if isinstance(v, str):
                v = val_str(v)
            if v.prefix == prefix_str:
                return v
            raise AssertionError(f"Expected id to have prefix {prefix_str}, got {v.prefix}")

        python_schema = core_schema.chain_schema(
            [
                core_schema.no_info_plain_validator_function(val_prefix),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=core_schema.chain_schema(
                [
                    core_schema.str_schema(),
                    core_schema.no_info_before_validator_function(val_str, python_schema),
                ]
            ),
            python_schema=python_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: str(x)),
        )
