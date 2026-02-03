"""Test SQLModel integration with UPLID."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select

from uplid import UPLID
from uplid.sqlalchemy import uplid_field

from .conftest import OrgId, OrgIdFactory, UserId, UserIdFactory


class User(SQLModel, table=True):
    """User model using SQLModel with UPLID via uplid_field helper."""

    __tablename__ = "sqlmodel_users"

    id: UserId = uplid_field(UserId, default_factory=UserIdFactory, primary_key=True)
    name: str
    org_id: OrgId | None = uplid_field(OrgId, default=None)


@pytest.fixture
def engine():
    """Create a fresh in-memory SQLite engine for SQLModel."""
    eng = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


class TestSQLModelBasics:
    """Test basic SQLModel + UPLID functionality."""

    def test_create_and_retrieve(self, engine) -> None:
        """Test creating and retrieving a user with UPLID."""
        with Session(engine) as session:
            user = User(name="Alice")
            session.add(user)
            session.commit()
            session.refresh(user)

            # Check the ID was generated
            assert user.id is not None
            assert user.id.prefix == "usr"

            # Retrieve and check type
            row = session.exec(select(User)).first()
            assert row is not None
            assert isinstance(row.id, UPLID)
            assert row.id == user.id

    def test_assign_uplid_directly(self, engine) -> None:
        """Test assigning UPLID directly."""
        user_id = UserIdFactory()
        org_id = OrgIdFactory()

        with Session(engine) as session:
            user = User(id=user_id, name="Bob", org_id=org_id)
            session.add(user)
            session.commit()

            row = session.exec(select(User)).first()
            assert row is not None
            assert row.id == user_id
            assert row.org_id == org_id

    def test_query_by_uplid(self, engine) -> None:
        """Test querying by UPLID."""
        user_id = UserIdFactory()

        with Session(engine) as session:
            session.add(User(id=user_id, name="Charlie"))
            session.commit()

            row = session.exec(select(User).where(User.id == user_id)).first()
            assert row is not None
            assert row.name == "Charlie"

    def test_pydantic_serialization(self) -> None:
        """Test that Pydantic serialization still works."""
        user = User(name="Dave")

        # model_dump should serialize UPLID to string
        data = user.model_dump()
        assert isinstance(data["id"], str)
        assert data["id"].startswith("usr_")

        # model_dump_json should work
        json_str = user.model_dump_json()
        assert "usr_" in json_str

    def test_pydantic_validation(self) -> None:
        """Test that Pydantic validation works."""
        user_id = UserIdFactory()

        # Should accept string
        user = User.model_validate({"id": str(user_id), "name": "Eve"})
        assert user.id == user_id

        # Should accept UPLID object
        user = User.model_validate({"id": user_id, "name": "Eve"})
        assert user.id == user_id

    def test_wrong_prefix_rejected(self) -> None:
        """Test that wrong prefix is rejected by Pydantic."""
        org_id = OrgIdFactory()  # Wrong prefix for id field

        with pytest.raises(ValidationError):
            User.model_validate({"id": str(org_id), "name": "Bad"})

    def test_nullable_field(self, engine) -> None:
        """Test nullable UPLID field."""
        with Session(engine) as session:
            user = User(name="Frank", org_id=None)
            session.add(user)
            session.commit()

            row = session.exec(select(User)).first()
            assert row is not None
            assert row.org_id is None

    def test_roundtrip_preserves_datetime(self, engine) -> None:
        """Test that datetime is preserved through DB roundtrip."""
        user_id = UserIdFactory()
        original_dt = user_id.datetime

        with Session(engine) as session:
            session.add(User(id=user_id, name="Grace"))
            session.commit()

            row = session.exec(select(User)).first()
            assert row is not None
            assert row.id.datetime == original_dt
