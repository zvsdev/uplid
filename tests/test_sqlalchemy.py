from __future__ import annotations

import pytest
import sqlalchemy.exc
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from uplid import UPLID
from uplid.sqlalchemy import uplid_column

from .conftest import OrgId, OrgIdFactory, UserId, UserIdFactory


class Base(DeclarativeBase):
    pass


class User(Base):
    """User model using uplid_column helper - columns are typed as UPLID."""

    __tablename__ = "users"

    id: Mapped[UserId] = uplid_column(UserId, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    org_id: Mapped[OrgId | None] = uplid_column(OrgId, nullable=True)


@pytest.fixture
def engine():
    """Create a fresh in-memory SQLite engine with tables."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


class TestUPLIDColumn:
    """Test the uplid_column helper with automatic serialization."""

    def test_store_and_retrieve_as_uplid(self, engine) -> None:
        """Columns return UPLID objects, not strings."""
        user_id = UserIdFactory()

        with Session(engine) as session:
            user = User(id=user_id, name="Alice")
            session.add(user)
            session.commit()

            row = session.execute(select(User)).scalar_one()
            # Returns UPLID, not string
            assert isinstance(row.id, UPLID)
            assert row.id == user_id
            assert row.id.prefix == "usr"

    def test_assign_uplid_directly(self, engine) -> None:
        """Can assign UPLID objects directly to columns."""
        user_id = UserIdFactory()
        org_id = OrgIdFactory()

        with Session(engine) as session:
            user = User(id=user_id, name="Bob", org_id=org_id)
            session.add(user)
            session.commit()

            row = session.execute(select(User)).scalar_one()
            assert row.id == user_id
            assert row.org_id == org_id

    def test_nullable_uplid_column(self, engine) -> None:
        """Nullable UPLID columns work correctly."""
        user_id = UserIdFactory()

        with Session(engine) as session:
            user = User(id=user_id, name="Charlie", org_id=None)
            session.add(user)
            session.commit()

            row = session.execute(select(User)).scalar_one()
            assert row.org_id is None

    def test_query_by_uplid(self, engine) -> None:
        """Can query using UPLID objects."""
        user_id = UserIdFactory()

        with Session(engine) as session:
            session.add(User(id=user_id, name="Dave"))
            session.commit()

            row = session.execute(select(User).where(User.id == user_id)).scalar_one()
            assert row.name == "Dave"

    def test_query_by_string(self, engine) -> None:
        """Can also query using string representation."""
        user_id = UserIdFactory()

        with Session(engine) as session:
            session.add(User(id=user_id, name="Eve"))
            session.commit()

            row = session.execute(select(User).where(User.id == str(user_id))).scalar_one()
            assert row.name == "Eve"

    def test_preserves_datetime(self, engine) -> None:
        """UPLID datetime is preserved through database roundtrip."""
        user_id = UserIdFactory()
        original_datetime = user_id.datetime

        with Session(engine) as session:
            session.add(User(id=user_id, name="Frank"))
            session.commit()

            row = session.execute(select(User)).scalar_one()
            assert row.id.datetime == original_datetime

    def test_ordering_matches_creation_order(self, engine) -> None:
        """UUIDv7-based IDs sort chronologically."""
        ids = [UserIdFactory() for _ in range(5)]

        with Session(engine) as session:
            for i, uid in enumerate(ids):
                session.add(User(id=uid, name=f"User{i}"))
            session.commit()

            rows = session.execute(select(User).order_by(User.id)).scalars().all()
            retrieved_ids = [r.id for r in rows]
            assert retrieved_ids == ids

    def test_filter_by_org(self, engine) -> None:
        """Can filter by foreign key UPLID."""
        org1 = OrgIdFactory()
        org2 = OrgIdFactory()

        with Session(engine) as session:
            session.add(User(id=UserIdFactory(), name="Alice", org_id=org1))
            session.add(User(id=UserIdFactory(), name="Bob", org_id=org1))
            session.add(User(id=UserIdFactory(), name="Charlie", org_id=org2))
            session.commit()

            org1_users = session.execute(select(User).where(User.org_id == org1)).scalars().all()
            assert len(org1_users) == 2
            assert {u.name for u in org1_users} == {"Alice", "Bob"}


class TestUPLIDType:
    """Test the UPLIDType TypeDecorator directly."""

    def test_accepts_string_input(self, engine) -> None:
        """UPLIDType accepts string input and converts to UPLID on read."""
        user_id = UserIdFactory()

        with Session(engine) as session:
            # Pass string instead of UPLID
            user = User(id=str(user_id), name="Test")
            session.add(user)
            session.commit()

            row = session.execute(select(User)).scalar_one()
            assert isinstance(row.id, UPLID)
            assert row.id == user_id


class TestUplitColumnErrors:
    """Test error handling in uplid_column."""

    def test_rejects_unparameterized_type(self) -> None:
        """uplid_column requires a parameterized UPLID type."""
        with pytest.raises(TypeError, match="must be parameterized"):
            uplid_column(UPLID)

    def test_rejects_wrong_prefix_uplid_on_write(self, engine) -> None:
        """Storing a UPLID with wrong prefix raises error."""
        org_id = OrgIdFactory()  # org_ prefix, but column expects usr_

        # Trying to store org_id in a UserId column should fail
        # SQLAlchemy wraps errors in StatementError
        with (
            Session(engine) as session,
            pytest.raises(sqlalchemy.exc.StatementError, match="Expected prefix 'usr'"),
        ):
            user = User(id=org_id, name="Bad")
            session.add(user)
            session.flush()

    def test_rejects_wrong_prefix_string_on_write(self, engine) -> None:
        """Storing a string with wrong prefix raises error."""
        org_id = OrgIdFactory()

        with (
            Session(engine) as session,
            pytest.raises(sqlalchemy.exc.StatementError, match="Expected prefix"),
        ):
            user = User(id=str(org_id), name="Bad")
            session.add(user)
            session.flush()

    def test_rejects_invalid_string_on_write(self, engine) -> None:
        """Storing an invalid string raises error."""
        with (
            Session(engine) as session,
            pytest.raises(sqlalchemy.exc.StatementError, match="Expected prefix"),
        ):
            user = User(id="not_a_valid_uplid", name="Bad")
            session.add(user)
            session.flush()


class TestSQLAlchemyTransactions:
    """Test transaction behavior with UPLID columns."""

    def test_rollback_does_not_persist(self, engine) -> None:
        user_id = UserIdFactory()

        with Session(engine) as session:
            session.add(User(id=user_id, name="Rollback"))
            session.rollback()

        with Session(engine) as session:
            count = session.execute(select(User)).scalars().all()
            assert len(count) == 0

    def test_unique_constraint_on_duplicate_id(self, engine) -> None:
        user_id = UserIdFactory()

        with Session(engine) as session:
            session.add(User(id=user_id, name="First"))
            session.commit()

        with Session(engine) as session:
            session.add(User(id=user_id, name="Duplicate"))
            with pytest.raises(sqlalchemy.exc.IntegrityError):
                session.commit()
