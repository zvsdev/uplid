from __future__ import annotations

import contextlib

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from uplid import UPLID, UPLIDError
from uplid.uplid import _base62_to_int

from .conftest import base62_uid_strategy, prefix_strategy


class TestParserFuzzing:
    @given(st.text())
    @settings(max_examples=500)
    def test_from_string_raises_uplid_error_or_succeeds(self, s: str) -> None:
        """Parser should only raise UPLIDError, never other exceptions."""
        with contextlib.suppress(UPLIDError):
            UPLID.from_string(s, "test")
        # Any other exception will fail the test

    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=500)
    def test_from_string_with_arbitrary_uid_part(self, uid_part: str) -> None:
        """Parser should handle any UID part gracefully."""
        with contextlib.suppress(UPLIDError):
            UPLID.from_string(f"usr_{uid_part}", "usr")

    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=200)
    def test_base62_decoder_raises_expected_errors(self, s: str) -> None:
        """Base62 decoder should only raise KeyError or ValueError."""
        try:
            _base62_to_int(s)
        except KeyError:
            pass  # Invalid character
        except ValueError:
            pass  # Too long


class TestPrefixFuzzing:
    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=500)
    def test_generate_raises_uplid_error_or_succeeds(self, prefix: str) -> None:
        """Generate should only raise UPLIDError for invalid prefixes."""
        with contextlib.suppress(UPLIDError):
            UPLID.generate(prefix)


class TestRoundtripInvariants:
    @given(prefix_strategy)
    @settings(max_examples=200)
    def test_generate_roundtrip(self, prefix: str) -> None:
        """Generated UPLID should survive roundtrip through string."""
        uid = UPLID.generate(prefix)
        parsed = UPLID.from_string(str(uid), prefix)
        assert uid == parsed

    @given(prefix_strategy)
    @settings(max_examples=200)
    def test_string_format_invariants(self, prefix: str) -> None:
        """String representation should have expected format."""
        uid = UPLID.generate(prefix)
        s = str(uid)
        assert s.startswith(f"{prefix}_")
        assert len(s) == len(prefix) + 1 + 22  # prefix + underscore + base62
        assert s.count("_") >= 1  # At least the separator

    @given(prefix_strategy)
    @settings(max_examples=200)
    def test_base62_uid_invariants(self, prefix: str) -> None:
        """Base62 UID should have expected properties."""
        uid = UPLID.generate(prefix)
        assert len(uid.base62_uid) == 22
        assert all(
            c in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            for c in uid.base62_uid
        )

    @given(prefix_strategy, base62_uid_strategy)
    @settings(max_examples=100)
    def test_valid_format_parses(self, prefix: str, uid: str) -> None:
        """Any valid-format string should parse without crashing."""
        s = f"{prefix}_{uid}"
        try:
            parsed = UPLID.from_string(s, prefix)
            assert parsed.prefix == prefix
            assert parsed.base62_uid == uid
        except UPLIDError:
            pass  # Some base62 values may not be valid UUIDs


class TestEdgeCases:
    def test_empty_string(self) -> None:
        with pytest.raises(UPLIDError, match="format"):
            UPLID.from_string("", "usr")

    def test_only_underscore(self) -> None:
        with pytest.raises(UPLIDError, match="snake_case"):
            UPLID.from_string("_", "usr")

    def test_many_underscores(self) -> None:
        with pytest.raises(UPLIDError, match="snake_case"):
            UPLID.from_string("___", "usr")

    def test_unicode_in_uid(self) -> None:
        with pytest.raises(UPLIDError, match="Invalid base62"):
            UPLID.from_string("usr_" + "é" * 22, "usr")

    def test_null_bytes(self) -> None:
        with pytest.raises(UPLIDError):
            UPLID.from_string("usr_\x00" + "0" * 21, "usr")

    def test_very_long_input(self) -> None:
        with pytest.raises(UPLIDError, match="at most 64"):
            UPLID.from_string("a" * 10000 + "_" + "0" * 22, "a" * 10000)

    def test_whitespace_in_prefix(self) -> None:
        with pytest.raises(UPLIDError, match="snake_case"):
            UPLID.generate("user id")

    def test_hyphen_in_prefix(self) -> None:
        with pytest.raises(UPLIDError, match="snake_case"):
            UPLID.generate("user-id")
