"""Shared test fixtures and Hypothesis strategies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pytest
from hypothesis import strategies as st

from uplid import UPLID, factory


if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine

# =============================================================================
# Common Type Aliases and Factories
# =============================================================================

UserId = UPLID[Literal["usr"]]
OrgId = UPLID[Literal["org"]]
ApiKeyId = UPLID[Literal["api_key"]]

UserIdFactory = factory(UserId)
OrgIdFactory = factory(OrgId)
ApiKeyIdFactory = factory(ApiKeyId)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

# Strategy for valid prefixes (snake_case, no consecutive underscores)
prefix_strategy = st.from_regex(r"[a-z]([a-z_]*[a-z])?", fullmatch=True).filter(
    lambda s: "__" not in s and len(s) <= 20
)

# Strategy for valid base62 characters
base62_strategy = st.sampled_from("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")

# Strategy for valid 22-char base62 UIDs
base62_uid_strategy = st.text(base62_strategy, min_size=22, max_size=22)


# =============================================================================
# SQLAlchemy Fixtures
# =============================================================================


@pytest.fixture
def sqlalchemy_engine() -> Iterator[Engine]:
    """Create a fresh in-memory SQLite engine with tables."""
    from sqlalchemy import String, create_engine
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

    from uplid.sqlalchemy import uplid_column

    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "users"
        id: Mapped[UserId] = uplid_column(UserId, primary_key=True)
        name: Mapped[str] = mapped_column(String(100))
        org_id: Mapped[OrgId | None] = uplid_column(OrgId, nullable=True)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def sqlmodel_engine() -> Iterator[Engine]:
    """Create a fresh in-memory SQLite engine for SQLModel."""
    from sqlalchemy import create_engine
    from sqlmodel import SQLModel

    from uplid.sqlalchemy import uplid_field

    class User(SQLModel, table=True):
        __tablename__ = "sqlmodel_users"
        id: UserId = uplid_field(UserId, default_factory=UserIdFactory, primary_key=True)
        name: str
        org_id: OrgId | None = uplid_field(OrgId, default=None)

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()
