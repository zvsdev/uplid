from typing import Literal

import pytest
from base62 import decode
from pydantic import BaseModel, Field
from ulid import ULID

from prefixed_id import PrefixedId

UserId = PrefixedId[Literal["usr"]]
WorkspaceId = PrefixedId[Literal["wrkspace"]]

test_id = PrefixedId.generate("usr")


class User(BaseModel):
    id: UserId = Field(default_factory=UserId.factory("usr"))


def test_it_can_generate_a_valid_id():
    user_id = PrefixedId.generate("usr")

    assert isinstance(user_id, PrefixedId)
    assert user_id.prefix == "usr"
    assert isinstance(user_id.uid, ULID)
    assert ULID.from_int(decode(user_id.encoded_uid))


def test_it_can_load_from_a_string():
    user_id = PrefixedId.from_string(str(test_id), "usr")

    assert isinstance(user_id, PrefixedId)
    assert user_id.prefix == "usr"
    assert isinstance(user_id.uid, ULID)


def test_it_raises_on_an_invalid_string() -> None:
    with pytest.raises(ValueError):
        PrefixedId.from_string("not_a_valid_id", "usr")


def test_it_raises_on_valid_prefix_but_missing_uid() -> None:
    with pytest.raises(ValueError):
        PrefixedId.from_string("usr_", "usr")


def test_it_raises_on_a_valid_prefix_but_invalid_uid() -> None:
    with pytest.raises(ValueError):
        PrefixedId.from_string("usr_00000000000000000000000000", "usr")


def test_it_can_instantiate_and_use_a_pydantic_model():
    user_id = PrefixedId.generate("usr")

    user = User(id=user_id)

    assert user.id == user_id


def test_it_can_instantiate_using_a_factory():
    user = User()

    assert isinstance(user.id, PrefixedId)
    assert user.id.prefix == "usr"


def test_it_raises_a_value_error_when_the_prefix_is_wrong() -> None:
    with pytest.raises(ValueError):
        PrefixedId.from_string(str(test_id), "not_usr")


def test_it_serializes_to_and_from_a_dict() -> None:
    user = User()

    user_dict = user.model_dump()

    rehydrated_user = User(**user_dict)

    assert rehydrated_user == user


def test_it_serializes_to_and_from_json() -> None:
    user = User()

    user_json = user.model_dump_json()

    rehydrated_user = User.model_validate_json(user_json)
    assert rehydrated_user == user
