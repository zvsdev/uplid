from datetime import datetime as Datetime
from typing import Any, Callable, Generic, Type, TypeVar, Union, get_args, get_origin

from ksuid import KsuidMs
from pydantic import GetCoreSchemaHandler, ValidationError
from pydantic_core import CoreSchema, PydanticCustomError, core_schema
from typing_extensions import LiteralString, Self

PREFIX = TypeVar("PREFIX", bound=LiteralString)


class UPLID(Generic[PREFIX]):
    """
    A class representing an ID with a prefixed lteral string identifier. The UID portion is managed using the KSUID
    format encoded via base62.

    Attributes:
        prefix (PREFIX): A string literal prefix for the ID. Can be specified as a type param or infered from args
        uid (KsuidMs): The KsuidMs object representing the unique identifier.

    Methods:
        from_string(string: str, prefix: PREFIX): Class method to create an instance of PrefixedId from a
            base62 string representation.
        generate(prefix: PREFIX): Class method to generate a new PrefixedId with a given prefix, optionally can be generated
        for a specific datetime.

    Raises:
        ValueError: If the string representation does not conform to the expected format, if prefix
            contains non-alphabetic characters, is not lowercase, or does not match the expected prefix.

    Note:
        This class requires a literal string as a type parameter for PREFIX. It integrates with Pydantic
        for validation and serialization purposes.
    """

    prefix: PREFIX
    uid: KsuidMs

    def __init__(self, prefix: PREFIX, uid: Union[str, KsuidMs]) -> None:
        self.prefix = prefix
        if isinstance(uid, str):
            self.uid = self._validate_uid(uid)
        else:
            self.uid = uid

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"{self.prefix}_{self.uid}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.prefix == other.prefix and self.uid == other.uid
        return False

    def __gt__(self, other: Self) -> bool:
        if isinstance(other, self.__class__):
            if self.prefix == other.prefix:
                return self.uid > other.uid
            return self.prefix > other.prefix
        raise TypeError(f"Cannot compare {self.__class__} with {other.__class__}")

    def __lt__(self, other: Self) -> bool:
        if isinstance(other, self.__class__):
            if self.prefix == other.prefix:
                return self.uid < other.uid
            return self.prefix < other.prefix
        raise TypeError(f"Cannot compare {self.__class__} with {other.__class__}")

    def __gte__(self, other: Self) -> bool:
        if isinstance(other, self.__class__):
            if self == other:
                return True
            return self > other
        raise TypeError(f"Cannot compare {self.__class__} with {other.__class__}")

    def __lte__(self, other: Self) -> bool:
        if isinstance(other, self.__class__):
            if self == other:
                return True
            return self < other
        raise TypeError(f"Cannot compare {self.__class__} with {other.__class__}")

    @staticmethod
    def _validate_uid(v: str) -> KsuidMs:
        if len(v) != 27:
            raise ValueError(f"Expected encoded_uid to be 27 characters long, got {len(v)}")
        try:
            return KsuidMs.from_base62(v)
        except OverflowError as e:
            raise ValueError(f"Invalid encoded_uid: {v}") from e

    @property
    def datetime(self) -> Datetime:
        return self.uid.datetime

    @property
    def timestamp(self) -> float:
        return self.uid.timestamp

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
        uid = cls._validate_uid(encoded_uid)
        return cls(prefix, uid)

    @classmethod
    def generate(cls, prefix: PREFIX, at: Union[Datetime, None] = None) -> Self:
        return cls(prefix, KsuidMs(at))

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        origin = get_origin(source_type)
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

        def val_str(v: str) -> UPLID[PREFIX]:
            try:
                prefixed_id = cls.from_string(v, prefix_str)
            except ValueError as e:
                raise AssertionError(e) from e
            return prefixed_id

        def val_prefix(v: Union[UPLID[PREFIX], str]) -> UPLID[PREFIX]:
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


def _get_prefix(uplid_type: Type[UPLID[PREFIX]]) -> PREFIX:
    literal_type = uplid_type.__args__[0]  # type: ignore
    return literal_type.__args__[0]  # type: ignore


def factory(uplid_type: Type[UPLID[PREFIX]]) -> Callable[[], UPLID[PREFIX]]:
    prefix = _get_prefix(uplid_type)

    def f() -> UPLID[PREFIX]:
        return UPLID.generate(prefix)

    return f


def validator(uplid_type: Type[UPLID[PREFIX]]) -> Callable[[str], UPLID[PREFIX]]:
    prefix = _get_prefix(uplid_type)

    def f(v: str) -> UPLID[PREFIX]:
        try:
            return UPLID.from_string(v, prefix)
        except ValueError as e:
            raise ValidationError.from_exception_data(
                f"{prefix.capitalize()}Id",
                [
                    {
                        "loc": (f"{prefix}_id",),
                        "input": v,
                        "type": PydanticCustomError("value_error", str(e)),
                    }
                ],
            ) from e

    return f
