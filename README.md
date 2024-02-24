# Prefixed Id

A pydantic compatible, human friendly prefixed id.

Uses Literal string types to enforce typing at both runtime (via pydantic) and during static analysis.

UIDs underneath are ULIDS which are then encoded with base62.
