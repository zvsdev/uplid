from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest


UserId = "UPLID[Literal['usr']]"  # Type alias placeholder


class TestUPLIDGeneration:
    def test_generate_creates_valid_uplid(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        assert uid.prefix == "usr"
        assert isinstance(uid.uid, UUID)

    def test_generate_rejects_uppercase_prefix(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="snake_case"):
            UPLID.generate("USR")

    def test_generate_rejects_prefix_starting_with_underscore(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="snake_case"):
            UPLID.generate("_usr")

    def test_generate_rejects_prefix_ending_with_underscore(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="snake_case"):
            UPLID.generate("usr_")

    def test_generate_accepts_snake_case_prefix(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("api_key")
        assert uid.prefix == "api_key"

    def test_generate_accepts_multi_underscore_prefix(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("org_member_role")
        assert uid.prefix == "org_member_role"

    def test_generate_accepts_single_char_prefix(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("x")
        assert uid.prefix == "x"


class TestUPLIDStringConversion:
    def test_str_format(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        s = str(uid)
        assert s.startswith("usr_")
        assert len(s) == 4 + 22  # prefix + underscore + base62

    def test_repr_shows_values(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        r = repr(uid)
        assert r.startswith("UPLID(")
        assert "'usr'" in r


class TestUPLIDParsing:
    def test_from_string_roundtrip(self) -> None:
        from uplid import UPLID

        original = UPLID.generate("usr")
        parsed = UPLID.from_string(str(original), "usr")
        assert original == parsed

    def test_from_string_with_underscore_prefix(self) -> None:
        from uplid import UPLID

        original = UPLID.generate("api_key")
        parsed = UPLID.from_string(str(original), "api_key")
        assert original == parsed

    def test_from_string_rejects_missing_underscore(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="format"):
            UPLID.from_string("nounderscore", "usr")

    def test_from_string_rejects_wrong_prefix(self) -> None:
        from uplid import UPLID, UPLIDError

        uid = UPLID.generate("usr")
        with pytest.raises(UPLIDError, match="Expected prefix"):
            UPLID.from_string(str(uid), "org")

    def test_from_string_rejects_invalid_uid_length(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="22 characters"):
            UPLID.from_string("usr_tooshort", "usr")

    def test_from_string_rejects_invalid_base62(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="Invalid base62"):
            UPLID.from_string("usr_!!!!!!!!!!!!!!!!!!!!!!", "usr")


class TestUPLIDProperties:
    def test_datetime_property(self) -> None:
        from datetime import timedelta

        from uplid import UPLID

        before = datetime.now(UTC)
        uid = UPLID.generate("usr")
        after = datetime.now(UTC)

        # Allow 1ms tolerance due to millisecond precision in UUIDv7
        tolerance = timedelta(milliseconds=1)
        assert before - tolerance <= uid.datetime <= after + tolerance

    def test_timestamp_property(self) -> None:
        from uplid import UPLID

        before = datetime.now(UTC).timestamp()
        uid = UPLID.generate("usr")
        after = datetime.now(UTC).timestamp()

        # Allow 1ms tolerance due to millisecond precision in UUIDv7
        tolerance = 0.001
        assert before - tolerance <= uid.timestamp <= after + tolerance

    def test_base62_uid_is_cached(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        first = uid.base62_uid
        second = uid.base62_uid
        assert first is second  # Same object, not just equal


class TestUPLIDPickle:
    def test_pickle_roundtrip(self) -> None:
        import pickle

        from uplid import UPLID

        original = UPLID.generate("usr")
        pickled = pickle.dumps(original)
        restored = pickle.loads(pickled)
        assert original == restored
        assert original.prefix == restored.prefix
        assert original.uid == restored.uid

    def test_pickle_with_underscore_prefix(self) -> None:
        import pickle

        from uplid import UPLID

        original = UPLID.generate("api_key")
        restored = pickle.loads(pickle.dumps(original))
        assert original == restored


class TestUPLIDCopy:
    def test_copy_returns_self(self) -> None:
        import copy

        from uplid import UPLID

        uid = UPLID.generate("usr")
        copied = copy.copy(uid)
        assert copied is uid  # Same object, not a copy

    def test_deepcopy_returns_self(self) -> None:
        import copy

        from uplid import UPLID

        uid = UPLID.generate("usr")
        copied = copy.deepcopy(uid)
        assert copied is uid  # Same object, not a copy


class TestUPLIDPrefixLimits:
    def test_rejects_prefix_exceeding_max_length(self) -> None:
        from uplid import UPLID, UPLIDError

        long_prefix = "a" * 65  # 65 > 64 max
        with pytest.raises(UPLIDError, match="at most 64 characters"):
            UPLID.generate(long_prefix)

    def test_accepts_prefix_at_max_length(self) -> None:
        from uplid import UPLID

        max_prefix = "a" * 64
        uid = UPLID.generate(max_prefix)
        assert uid.prefix == max_prefix
