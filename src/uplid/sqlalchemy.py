"""SQLAlchemy integration for UPLID.

Provides a TypeDecorator and helper for using UPLIDs as typed columns
that store as TEXT in the database.

Example:
    from typing import Literal
    from sqlalchemy.orm import DeclarativeBase, Mapped
    from uplid import UPLID
    from uplid.sqlalchemy import uplid_column

    UserId = UPLID[Literal["usr"]]
    OrgId = UPLID[Literal["org"]]

    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "users"

        id: Mapped[UserId] = uplid_column(UserId, primary_key=True)
        org_id: Mapped[OrgId | None] = uplid_column(OrgId)
        name: Mapped[str]
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, Unpack, get_args

from sqlalchemy import Text
from sqlalchemy.orm import mapped_column
from sqlalchemy.types import TypeDecorator

from uplid import UPLID, UPLIDType


if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.engine import Dialect
    from sqlalchemy.orm import MappedColumn


class UPLIDColumnKwargs(TypedDict, total=False):
    """Keyword arguments for uplid_column, matching mapped_column's common options."""

    primary_key: bool
    nullable: bool
    default: object
    default_factory: Callable[[], object]
    index: bool
    unique: bool
    insert_default: object
    onupdate: object


class UPLIDColumn(TypeDecorator[UPLIDType]):
    """SQLAlchemy TypeDecorator for UPLID storage as TEXT.

    Automatically serializes UPLID objects to strings on write
    and deserializes back to UPLID objects on read.

    Args:
        prefix: The expected prefix for UPLIDs in this column.

    Example:
        id: Mapped[UserId] = mapped_column(UPLIDColumn("usr"), primary_key=True)
    """

    impl = Text
    cache_ok = True

    def __init__(self, prefix: str) -> None:
        """Initialize with the expected UPLID prefix."""
        self.prefix = prefix
        super().__init__()

    def process_bind_param(
        self,
        value: UPLIDType | str | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> str | None:
        """Convert UPLID to string for database storage."""
        if value is None:
            return None
        if isinstance(value, UPLIDType):
            return str(value)
        return value

    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> UPLIDType | None:
        """Convert database string to UPLID object."""
        if value is None:
            return None
        return UPLID.from_string(value, self.prefix)


def _extract_prefix[T](uplid_type: type[T]) -> str:
    """Extract prefix from a parameterized UPLID type like UPLID[Literal["usr"]]."""
    type_args = get_args(uplid_type)
    if not type_args:
        msg = f"UPLID type must be parameterized, got {uplid_type}"
        raise TypeError(msg)

    literal_args = get_args(type_args[0])
    if not literal_args:
        msg = f"Could not extract prefix from {uplid_type}"
        raise TypeError(msg)

    return literal_args[0]


def uplid_column[T](
    uplid_type: type[T],
    **kwargs: Unpack[UPLIDColumnKwargs],
) -> MappedColumn[T]:
    """Create a mapped_column for a UPLID type (pure SQLAlchemy).

    Infers the prefix from the type parameter, so you don't need to
    specify it twice.

    Args:
        uplid_type: A parameterized UPLID type like UPLID[Literal["usr"]].
        **kwargs: Additional arguments passed to mapped_column.
            Supports: primary_key, nullable, default, default_factory,
            index, unique, insert_default, onupdate.

    Returns:
        A mapped_column configured with the appropriate UPLIDColumn.

    Example:
        UserId = UPLID[Literal["usr"]]
        OrgId = UPLID[Literal["org"]]

        class User(Base):
            __tablename__ = "users"

            id: Mapped[UserId] = uplid_column(UserId, primary_key=True)
            org_id: Mapped[OrgId | None] = uplid_column(OrgId)
    """
    prefix = _extract_prefix(uplid_type)
    return mapped_column(UPLIDColumn(prefix), **kwargs)


def uplid_field[T](uplid_type: type[T], **kwargs: object) -> object:
    """Create a SQLModel Field for a UPLID type.

    Infers the prefix from the type parameter and configures sa_type
    automatically.

    Args:
        uplid_type: A parameterized UPLID type like UPLID[Literal["usr"]].
        **kwargs: Additional arguments passed to Field
            (e.g., primary_key=True, default_factory=factory, index=True).

    Returns:
        A SQLModel Field configured with the appropriate UPLIDColumn.

    Example:
        from sqlmodel import SQLModel
        from uplid import UPLID, factory
        from uplid.sqlalchemy import uplid_field

        UserId = UPLID[Literal["usr"]]
        UserIdFactory = factory(UserId)

        class User(SQLModel, table=True):
            id: UserId = uplid_field(UserId, default_factory=UserIdFactory, primary_key=True)
            org_id: OrgId | None = uplid_field(OrgId, default=None)
    """
    # Import here to avoid hard dependency on sqlmodel
    from sqlmodel import Field

    prefix = _extract_prefix(uplid_type)
    return Field(sa_type=UPLIDColumn(prefix), **kwargs)


__all__ = ["UPLIDColumn", "uplid_column", "uplid_field"]
