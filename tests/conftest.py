"""Shared test fixtures and Hypothesis strategies."""

from __future__ import annotations

from hypothesis import strategies as st


# Hypothesis strategy for valid prefixes (snake_case, no consecutive underscores)
prefix_strategy = st.from_regex(r"[a-z]([a-z_]*[a-z])?", fullmatch=True).filter(
    lambda s: "__" not in s and len(s) <= 20
)

# Strategy for valid base62 characters
base62_strategy = st.sampled_from("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")

# Strategy for valid 22-char base62 UIDs
base62_uid_strategy = st.text(base62_strategy, min_size=22, max_size=22)
