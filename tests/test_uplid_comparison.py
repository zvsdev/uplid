from __future__ import annotations

from uuid import UUID, uuid7

from hypothesis import given, settings
from hypothesis import strategies as st

from uplid import UPLID

from .conftest import prefix_strategy


class TestUPLIDEquality:
    def test_equal_uplids_are_equal(self) -> None:
        uid1 = UPLID.generate("usr")
        uid2 = UPLID.from_string(str(uid1), "usr")
        assert uid1 == uid2

    def test_different_prefixes_not_equal(self) -> None:
        u = uuid7()
        uid1 = UPLID("usr", u)
        uid2 = UPLID("org", u)
        assert uid1 != uid2

    def test_different_uuids_not_equal(self) -> None:
        uid1 = UPLID.generate("usr")
        uid2 = UPLID.generate("usr")
        assert uid1 != uid2

    def test_not_equal_to_string(self) -> None:
        uid = UPLID.generate("usr")
        assert uid != str(uid)

    def test_not_equal_to_none(self) -> None:
        uid = UPLID.generate("usr")
        assert uid != None  # noqa: E711

    @given(prefix_strategy)
    def test_equality_is_reflexive(self, prefix: str) -> None:
        uid = UPLID.generate(prefix)
        assert uid == uid

    @given(prefix_strategy)
    def test_equality_is_symmetric(self, prefix: str) -> None:
        uid1 = UPLID.generate(prefix)
        uid2 = UPLID.from_string(str(uid1), prefix)
        assert uid1 == uid2
        assert uid2 == uid1  # Symmetry: a == b implies b == a

    def test_equality_is_transitive(self) -> None:
        uid1 = UPLID.generate("usr")
        uid2 = UPLID.from_string(str(uid1), "usr")
        uid3 = UPLID.from_string(str(uid2), "usr")
        assert uid1 == uid2
        assert uid2 == uid3
        assert uid1 == uid3  # Transitivity: a == b and b == c implies a == c


class TestUPLIDHashing:
    def test_equal_uplids_have_equal_hashes(self) -> None:
        uid1 = UPLID.generate("usr")
        uid2 = UPLID.from_string(str(uid1), "usr")
        assert hash(uid1) == hash(uid2)

    @given(prefix_strategy)
    def test_hash_consistent_with_equality(self, prefix: str) -> None:
        uid1 = UPLID.generate(prefix)
        uid2 = UPLID.from_string(str(uid1), prefix)
        if uid1 == uid2:
            assert hash(uid1) == hash(uid2)

    def test_can_use_as_dict_key(self) -> None:
        uid = UPLID.generate("usr")
        d = {uid: "value"}
        assert d[uid] == "value"

    def test_can_use_in_set(self) -> None:
        uid1 = UPLID.generate("usr")
        uid2 = UPLID.from_string(str(uid1), "usr")
        uid3 = UPLID.generate("usr")

        s = {uid1, uid2, uid3}
        assert len(s) == 2  # uid1 and uid2 are equal


class TestUPLIDOrdering:
    def test_ordering_with_deterministic_uuids(self) -> None:
        # Use deterministic UUIDs to avoid time.sleep flakiness
        # UUIDv7 with earlier timestamp should sort first
        early_uuid = UUID("01900000-0000-7000-8000-000000000001")
        later_uuid = UUID("01900000-0001-7000-8000-000000000001")

        first = UPLID("usr", early_uuid)
        second = UPLID("usr", later_uuid)

        assert first < second
        assert second > first
        assert first <= second
        assert second >= first

    def test_sorts_by_prefix_first(self) -> None:
        # Same UUID, different prefixes - should sort by prefix
        u = uuid7()
        a = UPLID("aaa", u)
        z = UPLID("zzz", u)
        assert a < z

    def test_comparison_with_non_uplid_returns_not_implemented(self) -> None:
        uid = UPLID.generate("usr")
        assert uid.__lt__("string") == NotImplemented
        assert uid.__le__("string") == NotImplemented
        assert uid.__gt__("string") == NotImplemented
        assert uid.__ge__("string") == NotImplemented

    def test_ordering_transitivity(self) -> None:
        # Use deterministic UUIDs
        uuid1 = UUID("01900000-0000-7000-8000-000000000001")
        uuid2 = UUID("01900000-0001-7000-8000-000000000001")
        uuid3 = UUID("01900000-0002-7000-8000-000000000001")

        a = UPLID("usr", uuid1)
        b = UPLID("usr", uuid2)
        c = UPLID("usr", uuid3)

        assert a < b
        assert b < c
        assert a < c  # Transitivity

    @given(st.lists(prefix_strategy, min_size=3, max_size=5, unique=True))
    @settings(max_examples=20)
    def test_sorting_is_stable(self, prefixes: list[str]) -> None:
        ids = [UPLID.generate(p) for p in prefixes]
        sorted_once = sorted(ids)
        sorted_twice = sorted(sorted_once)
        sorted_reverse = sorted(sorted(ids, reverse=True))
        assert sorted_once == sorted_twice == sorted_reverse
