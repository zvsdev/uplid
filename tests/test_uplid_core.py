from __future__ import annotations

import copy
import pickle
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid7

import pytest
from hypothesis import given, settings

from uplid import UPLID, UPLIDError, parse

from .conftest import prefix_strategy


class TestUPLIDGeneration:
    def test_generate_creates_valid_uplid(self) -> None:
        uid = UPLID.generate("usr")
        assert uid.prefix == "usr"
        assert isinstance(uid.uid, UUID)

    def test_generate_accepts_uppercase_prefix(self) -> None:
        uid = UPLID.generate("USR")
        assert uid.prefix == "USR"

    def test_generate_accepts_mixed_case_prefix(self) -> None:
        uid = UPLID.generate("ApiKey")
        assert uid.prefix == "ApiKey"

    def test_generate_rejects_prefix_starting_with_underscore(self) -> None:
        with pytest.raises(UPLIDError, match="letters and single underscores"):
            UPLID.generate("_usr")

    def test_generate_rejects_prefix_ending_with_underscore(self) -> None:
        with pytest.raises(UPLIDError, match="letters and single underscores"):
            UPLID.generate("usr_")

    def test_generate_accepts_snake_case_prefix(self) -> None:
        uid = UPLID.generate("api_key")
        assert uid.prefix == "api_key"

    def test_generate_accepts_multi_underscore_prefix(self) -> None:
        uid = UPLID.generate("org_member_role")
        assert uid.prefix == "org_member_role"

    def test_generate_accepts_single_char_prefix(self) -> None:
        uid = UPLID.generate("x")
        assert uid.prefix == "x"

    @given(prefix_strategy)
    @settings(max_examples=50)
    def test_generate_always_returns_valid_uplid(self, prefix: str) -> None:
        uid = UPLID.generate(prefix)
        assert uid.prefix == prefix
        assert isinstance(uid.uid, UUID)
        assert len(uid.base62_uid) == 22


class TestUPLIDStringConversion:
    def test_str_format(self) -> None:
        uid = UPLID.generate("usr")
        s = str(uid)
        assert s.startswith("usr_")
        assert len(s) == 4 + 22  # prefix + underscore + base62

    def test_repr_shows_prefix_and_uid(self) -> None:
        uid = UPLID.generate("usr")
        r = repr(uid)
        assert r.startswith("UPLID(")
        assert "'usr'" in r
        assert uid.base62_uid in r


class TestUPLIDParsing:
    def test_from_string_roundtrip(self) -> None:
        original = UPLID.generate("usr")
        parsed = UPLID.from_string(str(original), "usr")
        assert original == parsed

    def test_from_string_with_underscore_prefix(self) -> None:
        original = UPLID.generate("api_key")
        parsed = UPLID.from_string(str(original), "api_key")
        assert original == parsed

    def test_from_string_rejects_missing_underscore(self) -> None:
        with pytest.raises(UPLIDError, match="format"):
            UPLID.from_string("nounderscore", "usr")

    def test_from_string_rejects_wrong_prefix(self) -> None:
        uid = UPLID.generate("usr")
        with pytest.raises(UPLIDError, match="Expected prefix"):
            UPLID.from_string(str(uid), "org")

    def test_from_string_rejects_invalid_uid_length(self) -> None:
        with pytest.raises(UPLIDError, match="22 characters"):
            UPLID.from_string("usr_tooshort", "usr")

    def test_from_string_rejects_invalid_base62(self) -> None:
        with pytest.raises(UPLIDError, match="Invalid base62"):
            UPLID.from_string("usr_!!!!!!!!!!!!!!!!!!!!!!", "usr")


class TestUPLIDProperties:
    def test_datetime_property(self) -> None:
        before = datetime.now(UTC)
        uid = UPLID.generate("usr")
        after = datetime.now(UTC)

        tolerance = timedelta(milliseconds=1)
        assert before - tolerance <= uid.datetime <= after + tolerance

    def test_timestamp_property(self) -> None:
        before = datetime.now(UTC).timestamp()
        uid = UPLID.generate("usr")
        after = datetime.now(UTC).timestamp()

        tolerance = 0.001
        assert before - tolerance <= uid.timestamp <= after + tolerance

    def test_base62_uid_is_cached(self) -> None:
        uid = UPLID.generate("usr")
        first = uid.base62_uid
        second = uid.base62_uid
        assert first is second

    def test_datetime_and_timestamp_are_consistent(self) -> None:
        uid = UPLID.generate("usr")
        assert abs(uid.datetime.timestamp() - uid.timestamp) < 0.001


class TestUPLIDPickle:
    def test_pickle_roundtrip(self) -> None:
        original = UPLID.generate("usr")
        pickled = pickle.dumps(original)
        restored = pickle.loads(pickled)
        assert original == restored
        assert original.prefix == restored.prefix
        assert original.uid == restored.uid

    def test_pickle_with_underscore_prefix(self) -> None:
        original = UPLID.generate("api_key")
        restored = pickle.loads(pickle.dumps(original))
        assert original == restored

    @given(prefix_strategy)
    @settings(max_examples=20)
    def test_pickle_roundtrip_any_prefix(self, prefix: str) -> None:
        original = UPLID.generate(prefix)
        restored = pickle.loads(pickle.dumps(original))
        assert original == restored


class TestUPLIDCopy:
    def test_copy_returns_self(self) -> None:
        uid = UPLID.generate("usr")
        copied = copy.copy(uid)
        assert copied is uid

    def test_deepcopy_returns_self(self) -> None:
        uid = UPLID.generate("usr")
        copied = copy.deepcopy(uid)
        assert copied is uid


class TestUPLIDPrefixLimits:
    def test_rejects_prefix_exceeding_max_length(self) -> None:
        long_prefix = "a" * 65
        with pytest.raises(UPLIDError, match="at most 64 characters"):
            UPLID.generate(long_prefix)

    def test_accepts_prefix_at_max_length(self) -> None:
        max_prefix = "a" * 64
        uid = UPLID.generate(max_prefix)
        assert uid.prefix == max_prefix


class TestUPLIDPrefixValidation:
    def test_rejects_empty_prefix(self) -> None:
        with pytest.raises(UPLIDError, match="letters and single underscores"):
            UPLID.generate("")

    def test_rejects_consecutive_underscores(self) -> None:
        with pytest.raises(UPLIDError, match="letters and single underscores"):
            UPLID.generate("api__key")

    def test_rejects_numbers_in_prefix(self) -> None:
        with pytest.raises(UPLIDError, match="letters and single underscores"):
            UPLID.generate("user123")

    def test_accepts_mixed_case(self) -> None:
        uid = UPLID.generate("userId")
        assert uid.prefix == "userId"


class TestUPLIDFromStringEdgeCases:
    def test_rejects_empty_uid_part(self) -> None:
        with pytest.raises(UPLIDError, match="22 characters"):
            UPLID.from_string("usr_", "usr")

    def test_rejects_long_prefix_in_string(self) -> None:
        long_prefix = "a" * 65
        with pytest.raises(UPLIDError, match="at most 64 characters"):
            UPLID.from_string(f"{long_prefix}_{'0' * 22}", long_prefix)

    def test_rejects_consecutive_underscores_in_string(self) -> None:
        with pytest.raises(UPLIDError, match="letters and single underscores"):
            UPLID.from_string(f"api__key_{'0' * 22}", "api__key")


class TestUPLIDDirectConstruction:
    def test_init_validates_prefix(self) -> None:
        with pytest.raises(UPLIDError, match="letters and single underscores"):
            UPLID("123invalid", uuid7())

    def test_init_accepts_valid_prefix(self) -> None:
        u = uuid7()
        uid = UPLID("usr", u)
        assert uid.prefix == "usr"
        assert uid.uid == u


class TestParseHelper:
    def test_parse_creates_parser(self) -> None:
        UserId = UPLID[Literal["usr"]]
        parse_user_id = parse(UserId)

        uid = UPLID.generate("usr")
        parsed = parse_user_id(str(uid))
        assert parsed == uid

    def test_parse_rejects_wrong_prefix(self) -> None:
        UserId = UPLID[Literal["usr"]]
        parse_user_id = parse(UserId)

        org_id = UPLID.generate("org")
        with pytest.raises(UPLIDError, match="Expected prefix"):
            parse_user_id(str(org_id))

    def test_parse_rejects_invalid_string(self) -> None:
        UserId = UPLID[Literal["usr"]]
        parse_user_id = parse(UserId)

        with pytest.raises(UPLIDError):
            parse_user_id("not_valid")


class TestErrorMessageQuality:
    def test_prefix_error_shows_actual_value(self) -> None:
        with pytest.raises(UPLIDError, match="got '123bad'"):
            UPLID.generate("123bad")

    def test_wrong_prefix_error_shows_both_values(self) -> None:
        uid = UPLID.generate("usr")
        with pytest.raises(UPLIDError) as exc_info:
            UPLID.from_string(str(uid), "org")
        assert "usr" in str(exc_info.value)
        assert "org" in str(exc_info.value)

    def test_length_error_shows_actual_length(self) -> None:
        with pytest.raises(UPLIDError, match="got 5"):
            UPLID.from_string("usr_short", "usr")

    def test_max_length_error_shows_limit(self) -> None:
        with pytest.raises(UPLIDError, match="64"):
            UPLID.generate("a" * 100)
