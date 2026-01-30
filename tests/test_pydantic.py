from __future__ import annotations

from typing import Literal

import pytest
from pydantic import BaseModel, Field, ValidationError

from uplid import UPLID, UPLIDError, factory


UserId = UPLID[Literal["usr"]]
ApiKeyId = UPLID[Literal["api_key"]]


class TestPydanticValidation:
    def test_validates_from_string(self) -> None:
        class User(BaseModel):
            id: UserId

        uid = UPLID.generate("usr")
        user = User(id=str(uid))  # type: ignore[arg-type]
        assert user.id == uid

    def test_validates_from_uplid(self) -> None:
        class User(BaseModel):
            id: UserId

        uid = UPLID.generate("usr")
        user = User(id=uid)
        assert user.id == uid

    def test_rejects_wrong_prefix(self) -> None:
        class User(BaseModel):
            id: UserId

        org_id = UPLID.generate("org")
        with pytest.raises(ValidationError):
            User(id=org_id)

    def test_rejects_wrong_prefix_string(self) -> None:
        class User(BaseModel):
            id: UserId

        org_id = UPLID.generate("org")
        with pytest.raises(ValidationError):
            User(id=str(org_id))  # type: ignore[arg-type]

    def test_rejects_invalid_string(self) -> None:
        class User(BaseModel):
            id: UserId

        with pytest.raises(ValidationError):
            User(id="not_a_valid_id")  # type: ignore[arg-type]

    def test_works_with_default_factory(self) -> None:
        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))

        user = User()
        assert user.id.prefix == "usr"


class TestPydanticSerialization:
    def test_serializes_to_string_in_dict(self) -> None:
        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))

        user = User()
        data = user.model_dump()
        assert isinstance(data["id"], str)
        assert data["id"].startswith("usr_")

    def test_serializes_to_string_in_json(self) -> None:
        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))

        user = User()
        json_str = user.model_dump_json()
        assert '"usr_' in json_str

    def test_roundtrip_model_dump(self) -> None:
        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))

        user = User()
        data = user.model_dump()
        rehydrated = User(**data)
        assert rehydrated == user

    def test_roundtrip_json(self) -> None:
        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))

        user = User()
        json_str = user.model_dump_json()
        rehydrated = User.model_validate_json(json_str)
        assert rehydrated == user


class TestPydanticWithUnderscorePrefix:
    def test_validates_underscore_prefix(self) -> None:
        class ApiKey(BaseModel):
            id: ApiKeyId = Field(default_factory=factory(ApiKeyId))

        key = ApiKey()
        assert key.id.prefix == "api_key"

        # Roundtrip
        data = key.model_dump()
        rehydrated = ApiKey(**data)
        assert rehydrated == key


class TestPydanticErrorMessages:
    def test_error_on_unparameterized_uplid(self) -> None:
        with pytest.raises(UPLIDError, match="parameterized"):

            class Bad(BaseModel):
                id: UPLID

    def test_rejects_non_string_non_uplid(self) -> None:
        class User(BaseModel):
            id: UserId

        with pytest.raises(ValidationError):
            User(id=12345)  # type: ignore[arg-type]

        with pytest.raises(ValidationError):
            User(id={"key": "value"})  # type: ignore[arg-type]

        with pytest.raises(ValidationError):
            User(id=None)  # type: ignore[arg-type]


class TestHelperFunctionErrors:
    def test_factory_with_unparameterized_type_raises(self) -> None:
        with pytest.raises(UPLIDError, match="parameterized"):
            factory(UPLID)

    def test_parse_with_unparameterized_type_raises(self) -> None:
        from uplid import parse

        with pytest.raises(UPLIDError, match="parameterized"):
            parse(UPLID)
