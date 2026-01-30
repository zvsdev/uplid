# tests/conftest.py
from __future__ import annotations

from typing import Literal

import pytest
from hypothesis import strategies as st


# Hypothesis strategies
prefix_strategy = st.from_regex(r"[a-z]([a-z_]*[a-z])?", fullmatch=True).filter(
    lambda s: "__" not in s and len(s) <= 20
)

base62_char = st.sampled_from("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
base62_uid = st.text(base62_char, min_size=22, max_size=22)


@pytest.fixture
def user_id_type():
    """Return a UserId type alias."""
    from uplid import UPLID

    return UPLID[Literal["usr"]]


@pytest.fixture
def api_key_id_type():
    """Return an ApiKeyId type alias."""
    from uplid import UPLID

    return UPLID[Literal["api_key"]]
