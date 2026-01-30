from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st


class TestBase62Encoding:
    def test_zero_encodes_to_padded_zeros(self) -> None:
        from uplid.uplid import _int_to_base62

        assert _int_to_base62(0) == "0" * 22

    def test_max_uuid_fits_in_22_chars(self) -> None:
        from uplid.uplid import _int_to_base62

        max_128_bit = (1 << 128) - 1
        result = _int_to_base62(max_128_bit)
        assert len(result) == 22

    def test_roundtrip_preserves_value(self) -> None:
        from uplid.uplid import _base62_to_int, _int_to_base62

        original = 12345678901234567890
        encoded = _int_to_base62(original)
        decoded = _base62_to_int(encoded)
        assert decoded == original

    @given(st.integers(min_value=0, max_value=(1 << 128) - 1))
    def test_roundtrip_any_128bit_int(self, num: int) -> None:
        from uplid.uplid import _base62_to_int, _int_to_base62

        encoded = _int_to_base62(num)
        assert len(encoded) == 22
        decoded = _base62_to_int(encoded)
        assert decoded == num

    def test_invalid_char_raises(self) -> None:
        from uplid.uplid import _base62_to_int

        with pytest.raises(KeyError):
            _base62_to_int("invalid!")
