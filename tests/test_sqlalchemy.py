from __future__ import annotations

from typing import Literal

from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from uplid import UPLID, factory


UserId = UPLID[Literal["usr"]]
OrgId = UPLID[Literal["org"]]
UserIdFactory = factory(UserId)
OrgIdFactory = factory(OrgId)


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(87), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    org_id: Mapped[str | None] = mapped_column(String(87), nullable=True)


class TestSQLAlchemyStorage:
    def setup_method(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def test_store_and_retrieve_uplid(self) -> None:
        user_id = UPLID.generate("usr")

        with Session(self.engine) as session:
            user = UserRow(id=str(user_id), name="Alice")
            session.add(user)
            session.commit()

            # Retrieve
            row = session.execute(select(UserRow)).scalar_one()
            assert row.id == str(user_id)
            assert row.name == "Alice"

    def test_parse_retrieved_id(self) -> None:
        user_id = UPLID.generate("usr")

        with Session(self.engine) as session:
            session.add(UserRow(id=str(user_id), name="Bob"))
            session.commit()

            row = session.execute(select(UserRow)).scalar_one()
            parsed = UPLID.from_string(row.id, "usr")

            assert parsed == user_id
            assert parsed.prefix == "usr"
            assert parsed.datetime == user_id.datetime

    def test_query_by_id(self) -> None:
        user_id = UPLID.generate("usr")

        with Session(self.engine) as session:
            session.add(UserRow(id=str(user_id), name="Charlie"))
            session.commit()

            # Query by string ID
            row = session.execute(
                select(UserRow).where(UserRow.id == str(user_id))
            ).scalar_one()
            assert row.name == "Charlie"

    def test_multiple_users_with_org(self) -> None:
        org_id = UPLID.generate("org")
        user1_id = UPLID.generate("usr")
        user2_id = UPLID.generate("usr")

        with Session(self.engine) as session:
            session.add(UserRow(id=str(user1_id), name="Alice", org_id=str(org_id)))
            session.add(UserRow(id=str(user2_id), name="Bob", org_id=str(org_id)))
            session.commit()

            # Query by org
            rows = session.execute(
                select(UserRow).where(UserRow.org_id == str(org_id))
            ).scalars().all()
            assert len(rows) == 2
            assert {r.name for r in rows} == {"Alice", "Bob"}

    def test_id_ordering_matches_creation_order(self) -> None:
        # UUIDv7 IDs should sort chronologically
        ids = [UPLID.generate("usr") for _ in range(5)]

        with Session(self.engine) as session:
            for i, uid in enumerate(ids):
                session.add(UserRow(id=str(uid), name=f"User{i}"))
            session.commit()

            # Query ordered by ID
            rows = session.execute(
                select(UserRow).order_by(UserRow.id)
            ).scalars().all()

            # String ordering of base62 UUIDv7 preserves chronological order
            retrieved_ids = [UPLID.from_string(r.id, "usr") for r in rows]
            assert retrieved_ids == ids

    def test_max_prefix_length_fits_in_column(self) -> None:
        # Max prefix is 64 chars, total ID is 64 + 1 + 22 = 87 chars
        long_prefix = "a" * 64
        uid = UPLID.generate(long_prefix)
        assert len(str(uid)) == 87

        # This should fit in String(87)
        with Session(self.engine) as session:
            session.add(UserRow(id=str(uid), name="LongPrefix"))
            session.commit()

            row = session.execute(select(UserRow)).scalar_one()
            parsed = UPLID.from_string(row.id, long_prefix)
            assert parsed == uid


class TestSQLAlchemyTransactions:
    def setup_method(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def test_rollback_does_not_persist(self) -> None:
        user_id = UPLID.generate("usr")

        with Session(self.engine) as session:
            session.add(UserRow(id=str(user_id), name="Rollback"))
            session.rollback()

        with Session(self.engine) as session:
            count = session.execute(select(UserRow)).scalars().all()
            assert len(count) == 0

    def test_unique_constraint_on_duplicate_id(self) -> None:
        user_id = UPLID.generate("usr")

        with Session(self.engine) as session:
            session.add(UserRow(id=str(user_id), name="First"))
            session.commit()

        # Attempting to insert duplicate should raise
        import pytest
        import sqlalchemy.exc

        with Session(self.engine) as session:
            session.add(UserRow(id=str(user_id), name="Duplicate"))
            with pytest.raises(sqlalchemy.exc.IntegrityError):
                session.commit()
