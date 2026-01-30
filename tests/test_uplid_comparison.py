# tests/test_uplid_comparison.py
from __future__ import annotations

import time

from hypothesis import given, settings
from hypothesis import strategies as st


prefix_strategy = st.from_regex(r"[a-z]([a-z_]*[a-z])?", fullmatch=True).filter(
    lambda s: "__" not in s and len(s) <= 20
)


class TestUPLIDEquality:
    def test_equal_uplids_are_equal(self) -> None:
        from uplid import UPLID

        uid1 = UPLID.generate("usr")
        uid2 = UPLID.from_string(str(uid1), "usr")
        assert uid1 == uid2

    def test_different_prefixes_not_equal(self) -> None:
        from uuid import uuid7

        from uplid import UPLID

        # Same UUID, different prefix
        u = uuid7()
        uid1 = UPLID("usr", u)
        uid2 = UPLID("org", u)
        assert uid1 != uid2

    def test_different_uuids_not_equal(self) -> None:
        from uplid import UPLID

        uid1 = UPLID.generate("usr")
        uid2 = UPLID.generate("usr")
        assert uid1 != uid2

    def test_not_equal_to_string(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        assert uid != str(uid)

    def test_not_equal_to_none(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        assert uid != None  # noqa: E711

    @given(prefix_strategy)
    def test_equality_is_reflexive(self, prefix: str) -> None:
        from uplid import UPLID

        uid = UPLID.generate(prefix)
        assert uid == uid


class TestUPLIDHashing:
    def test_equal_uplids_have_equal_hashes(self) -> None:
        from uplid import UPLID

        uid1 = UPLID.generate("usr")
        uid2 = UPLID.from_string(str(uid1), "usr")
        assert hash(uid1) == hash(uid2)

    def test_can_use_as_dict_key(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        d = {uid: "value"}
        assert d[uid] == "value"

    def test_can_use_in_set(self) -> None:
        from uplid import UPLID

        uid1 = UPLID.generate("usr")
        uid2 = UPLID.from_string(str(uid1), "usr")
        uid3 = UPLID.generate("usr")

        s = {uid1, uid2, uid3}
        assert len(s) == 2  # uid1 and uid2 are equal


class TestUPLIDOrdering:
    def test_sorts_by_timestamp(self) -> None:
        from uplid import UPLID

        first = UPLID.generate("usr")
        time.sleep(0.002)  # Ensure different ms timestamp
        second = UPLID.generate("usr")
        time.sleep(0.002)
        third = UPLID.generate("usr")

        assert first < second < third
        assert sorted([third, first, second]) == [first, second, third]

    def test_sorts_by_prefix_first(self) -> None:
        from uplid import UPLID

        a = UPLID.generate("aaa")
        z = UPLID.generate("zzz")
        assert a < z

    def test_comparison_with_non_uplid_returns_not_implemented(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        assert uid.__lt__("string") == NotImplemented
        assert uid.__le__("string") == NotImplemented
        assert uid.__gt__("string") == NotImplemented
        assert uid.__ge__("string") == NotImplemented

    @given(st.lists(prefix_strategy, min_size=2, max_size=5))
    @settings(max_examples=20)
    def test_ordering_is_consistent(self, prefixes: list[str]) -> None:
        from uplid import UPLID

        ids = [UPLID.generate(p) for p in prefixes]
        sorted_ids = sorted(ids)
        assert sorted(sorted_ids) == sorted_ids
