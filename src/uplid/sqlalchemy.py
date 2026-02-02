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

from typing import TYPE_CHECKING, Any, get_args

from sqlalchemy import Text
from sqlalchemy.orm import mapped_column
from sqlalchemy.types import TypeDecorator

from uplid import UPLID


if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect
    from sqlalchemy.orm import MappedColumn


class UPLIDType(TypeDecorator[UPLID[Any]]):
    """SQLAlchemy TypeDecorator for UPLID storage as TEXT.

    Automatically serializes UPLID objects to strings on write
    and deserializes back to UPLID objects on read.

    Args:
        prefix: The expected prefix for UPLIDs in this column.

    Example:
        id: Mapped[UserId] = mapped_column(UPLIDType("usr"), primary_key=True)
    """

    impl = Text
    cache_ok = True

    def __init__(self, prefix: str) -> None:
        """Initialize with the expected UPLID prefix."""
        self.prefix = prefix
        super().__init__()

    def process_bind_param(
        self,
        value: UPLID[Any] | str | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> str | None:
        """Convert UPLID to string for database storage."""
        if value is None:
            return None
        if isinstance(value, UPLID):
            return str(value)
        return value

    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> UPLID[Any] | None:
        """Convert database string to UPLID object."""
        if value is None:
            return None
        return UPLID.from_string(value, self.prefix)


def uplid_column[T](uplid_type: type[T], **kwargs: Any) -> MappedColumn[T]:  # noqa: ANN401
    """Create a mapped_column for a UPLID type.

    Infers the prefix from the type parameter, so you don't need to
    specify it twice.

    Args:
        uplid_type: A parameterized UPLID type like UPLID[Literal["usr"]].
        **kwargs: Additional arguments passed to mapped_column
            (e.g., primary_key=True, default=factory, nullable=True).

    Returns:
        A mapped_column configured with the appropriate UPLIDType.

    Example:
        UserId = UPLID[Literal["usr"]]
        OrgId = UPLID[Literal["org"]]

        class User(Base):
            __tablename__ = "users"

            id: Mapped[UserId] = uplid_column(UserId, primary_key=True)
            org_id: Mapped[OrgId | None] = uplid_column(OrgId)
    """
    # Extract prefix from UPLID[Literal["usr"]] -> "usr"
    type_args = get_args(uplid_type)
    if not type_args:
        msg = f"UPLID type must be parameterized, got {uplid_type}"
        raise TypeError(msg)

    literal_args = get_args(type_args[0])
    if not literal_args:
        msg = f"Could not extract prefix from {uplid_type}"
        raise TypeError(msg)

    prefix = literal_args[0]
    return mapped_column(UPLIDType(prefix), **kwargs)


__all__ = ["UPLIDType", "uplid_column"]
