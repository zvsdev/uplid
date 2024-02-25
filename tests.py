import time
from typing import Literal

import pytest
from ksuid import KsuidMs
from pydantic import BaseModel, Field

from lpid import LPID, factory

UserId = LPID[Literal["usr"]]
WorkspaceId = LPID[Literal["wrkspace"]]

UserIdFactory = factory(UserId)
WorkspaceIdFactory = factory(WorkspaceId)
test_id = UserIdFactory()


class User(BaseModel):
    id: UserId = Field(default_factory=factory(UserId))


class Workspace(BaseModel):
    id: WorkspaceId = Field(default_factory=factory(WorkspaceId))


def test_it_can_generate_a_valid_id():
    user_id = UserIdFactory()

    assert isinstance(user_id, LPID)
    assert user_id.prefix == "usr"
    assert isinstance(user_id.uid, KsuidMs)


def test_it_can_load_from_a_string() -> None:
    user_id = LPID.from_string(str(test_id), "usr")

    assert isinstance(user_id, LPID)
    assert user_id.prefix == "usr"
    assert isinstance(user_id.uid, KsuidMs)


def test_it_raises_on_an_invalid_string() -> None:
    with pytest.raises(ValueError):
        LPID.from_string("not_a_valid_id", "usr")


def test_it_raises_on_valid_prefix_but_missing_uid() -> None:
    with pytest.raises(ValueError):
        LPID.from_string("usr_", "usr")


def test_it_raises_on_a_valid_prefix_but_invalid_uid() -> None:
    with pytest.raises(ValueError):
        LPID.from_string("usr_00000000000000000000000000", "usr")


def test_it_can_instantiate_and_use_a_pydantic_model() -> None:
    user_id = UserIdFactory()

    user = User(id=user_id)

    assert user.id == user_id


def test_it_can_instantiate_using_a_factory() -> None:
    user = User()

    assert isinstance(user.id, LPID)
    assert user.id.prefix == "usr"


def test_it_raises_a_value_error_when_the_prefix_is_wrong() -> None:
    with pytest.raises(ValueError):
        LPID.from_string(str(test_id), "not_usr")


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


def test_it_fails_to_serialize_to_and_from_a_dict_with_the_wrong_prefix() -> None:
    user = User()

    user_dict = user.model_dump()

    with pytest.raises(ValueError):
        Workspace(**user_dict)


def test_it_fails_to_serialize_to_and_from_json_with_the_wrong_prefix() -> None:
    user = User()

    user_json = user.model_dump_json()

    with pytest.raises(ValueError):
        Workspace.model_validate_json(user_json)


def test_it_orders_by_creation_time_given_enough_time() -> None:
    first = UserIdFactory()
    time.sleep(0.01)
    second = UserIdFactory()
    time.sleep(0.01)
    third = UserIdFactory()

    assert sorted([third, first, second]) == [first, second, third]
