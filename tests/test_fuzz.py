from __future__ import annotations

import contextlib

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from uplid import UPLID, UPLIDError
from uplid.uplid import _base62_to_int


class TestParserFuzzing:
    @given(st.text())
    @settings(max_examples=500)
    def test_from_string_never_crashes(self, s: str) -> None:
        """Parser should raise UPLIDError, never crash."""
        with contextlib.suppress(UPLIDError):
            UPLID.from_string(s, "test")

    @given(st.text())
    @settings(max_examples=500)
    def test_from_string_with_arbitrary_prefix_never_crashes(self, s: str) -> None:
        """Parser should handle any prefix gracefully."""
        with contextlib.suppress(UPLIDError):
            UPLID.from_string(f"usr_{s}", "usr")

    @given(st.binary())
    @settings(max_examples=200)
    def test_base62_decoder_handles_arbitrary_bytes(self, b: bytes) -> None:
        """Base62 decoder should not crash on arbitrary input."""
        try:
            s = b.decode("utf-8", errors="ignore")
            _base62_to_int(s)
        except (KeyError, ValueError):
            pass  # Expected for invalid input


class TestPrefixFuzzing:
    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=500)
    def test_generate_validates_prefix(self, prefix: str) -> None:
        """Generate should validate prefix and never crash."""
        with contextlib.suppress(UPLIDError):
            UPLID.generate(prefix)


class TestEdgeCases:
    def test_empty_string(self) -> None:
        with pytest.raises(UPLIDError):
            UPLID.from_string("", "usr")

    def test_only_underscore(self) -> None:
        with pytest.raises(UPLIDError):
            UPLID.from_string("_", "usr")

    def test_many_underscores(self) -> None:
        with pytest.raises(UPLIDError):
            UPLID.from_string("___", "usr")

    def test_unicode_in_uid(self) -> None:
        with pytest.raises(UPLIDError):
            UPLID.from_string("usr_" + "é" * 22, "usr")

    def test_null_bytes(self) -> None:
        with pytest.raises(UPLIDError):
            UPLID.from_string("usr_\x00" * 22, "usr")

    def test_very_long_input(self) -> None:
        with pytest.raises(UPLIDError):
            UPLID.from_string("a" * 10000, "usr")
