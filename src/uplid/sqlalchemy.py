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

from typing import TYPE_CHECKING, Any, TypedDict, Unpack, cast

from sqlalchemy import Text
from sqlalchemy.orm import mapped_column
from sqlalchemy.types import TypeDecorator

from uplid import UPLID, UPLIDError, UPLIDType, _get_prefix


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
        """Convert UPLID to string for database storage.

        Validates that strings have the correct prefix before storing.
        This catches prefix mismatches at write time rather than read time.
        """
        if value is None:
            return None
        if isinstance(value, UPLIDType):
            if value.prefix != self.prefix:
                msg = f"Expected prefix {self.prefix!r}, got {value.prefix!r}"
                raise ValueError(msg)
            return str(value)
        # Validate string format and prefix before storing
        if isinstance(value, str):
            UPLID.from_string(value, self.prefix)  # Raises UPLIDError if invalid
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
    """Extract prefix from a parameterized UPLID type like UPLID[Literal["usr"]].

    Wraps _get_prefix to convert UPLIDError to TypeError for SQLAlchemy context.
    """
    try:
        return _get_prefix(uplid_type)  # type: ignore[arg-type]
    except UPLIDError as e:
        raise TypeError(str(e)) from e


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


class UPLIDFieldKwargs(TypedDict, total=False):
    """Keyword arguments for uplid_field, matching SQLModel Field's common options."""

    default: object
    default_factory: Callable[[], object]
    primary_key: bool
    index: bool
    unique: bool


def uplid_field[T](
    uplid_type: type[T],
    **kwargs: Unpack[UPLIDFieldKwargs],
) -> Any:  # noqa: ANN401 - return type matches SQLModel's Field
    """Create a SQLModel Field for a UPLID type.

    Infers the prefix from the type parameter and configures sa_type
    automatically.

    Args:
        uplid_type: A parameterized UPLID type like UPLID[Literal["usr"]].
        **kwargs: Additional arguments passed to Field.
            Supports: default, default_factory, primary_key, index, unique.

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
    # SQLModel's sa_type is incorrectly typed as type[Any] but accepts TypeEngine instances.
    # Use cast to satisfy the type checker until SQLModel fixes their stubs.
    sa_type = cast("type[Any]", UPLIDColumn(prefix))
    return Field(sa_type=sa_type, **kwargs)


__all__ = ["UPLIDColumn", "uplid_column", "uplid_field"]
