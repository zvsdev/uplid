# UPLID

Universal Prefixed Literal IDs - type-safe, human-readable identifiers for Python 3.14+.

[![CI](https://github.com/zvsdev/uplid/actions/workflows/ci.yml/badge.svg)](https://github.com/zvsdev/uplid/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/uplid)](https://pypi.org/project/uplid/)
[![Python](https://img.shields.io/pypi/pyversions/uplid)](https://pypi.org/project/uplid/)

## Features

- **Type-safe prefixes**: `UPLID[Literal["usr"]]` prevents mixing user IDs with org IDs (caught by type checkers like mypy/pyright/ty)
- **Human-readable**: `usr_0M3xL9kQ7vR2nP5wY1jZ4c` (Stripe-style prefixed IDs)
- **Time-sortable**: Built on UUIDv7 (RFC 9562) for natural chronological ordering
- **Compact**: 22-character base62 encoding (URL-safe, no special characters)
- **Stdlib UUIDs**: Uses Python 3.14's native `uuid7()` - no external UUID libraries
- **Pydantic 2 native**: Full validation and serialization support
- **Thread-safe**: ID generation is safe for concurrent use

## Installation

```bash
pip install uplid
# or
uv add uplid
```

Requires Python 3.14+ and Pydantic 2.10+.

## Quick Start

```python
from typing import Literal
from pydantic import BaseModel, Field
from uplid import UPLID, factory

# Define typed aliases and factories
UserId = UPLID[Literal["usr"]]
OrgId = UPLID[Literal["org"]]
UserIdFactory = factory(UserId)

# Use in Pydantic models
class User(BaseModel):
    id: UserId = Field(default_factory=UserIdFactory)
    org_id: OrgId

# Generate IDs
user_id = UPLID.generate("usr")
print(user_id)  # usr_0M3xL9kQ7vR2nP5wY1jZ4c

# Parse from string
parsed = UPLID.from_string("usr_0M3xL9kQ7vR2nP5wY1jZ4c", "usr")

# Access properties
print(parsed.datetime)   # 2026-01-30 12:34:56.789000+00:00
print(parsed.timestamp)  # 1738240496.789

# Type safety - type checkers (mypy/pyright/ty) catch prefix mismatches:
# user.org_id = user_id  # Type error: UserId is not compatible with OrgId
```

## Pydantic Serialization

UPLIDs serialize to strings and deserialize with validation:

```python
from pydantic import BaseModel, Field
from uplid import UPLID, factory

UserId = UPLID[Literal["usr"]]
UserIdFactory = factory(UserId)

class User(BaseModel):
    id: UserId = Field(default_factory=UserIdFactory)
    name: str

user = User(name="Alice")

# Serialize to dict - ID becomes string
user.model_dump()
# {"id": "usr_0M3xL9kQ7vR2nP5wY1jZ4c", "name": "Alice"}

# Serialize to JSON
json_str = user.model_dump_json()

# Deserialize - validates UPLID format and prefix
restored = User.model_validate_json(json_str)
assert restored.id == user.id

# Wrong prefix raises ValidationError
User(id="org_xxx...", name="Bad")  # ValidationError
```

## FastAPI Integration

```python
from typing import Annotated, Literal
from fastapi import Cookie, Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from uplid import UPLID, UPLIDError, factory, parse

UserId = UPLID[Literal["usr"]]
UserIdFactory = factory(UserId)
parse_user_id = parse(UserId)


class User(BaseModel):
    id: UserId = Field(default_factory=UserIdFactory)
    name: str


app = FastAPI()


# Dependency for validating path/query/header/cookie parameters
def get_user_id(user_id: str) -> UserId:
    try:
        return parse_user_id(user_id)
    except UPLIDError as e:
        raise HTTPException(422, f"Invalid user ID: {e}") from None


# Path parameter validation
@app.get("/users/{user_id}")
def get_user(user_id: Annotated[UserId, Depends(get_user_id)]) -> User:
    ...


# JSON body - Pydantic validates UPLID fields automatically
@app.post("/users")
def create_user(user: User) -> User:
    # user.id validated as UserId, wrong prefix returns 422
    return user


# Header validation
def get_user_id_from_header(x_user_id: Annotated[str, Header()]) -> UserId:
    try:
        return parse_user_id(x_user_id)
    except UPLIDError as e:
        raise HTTPException(422, f"Invalid X-User-Id header: {e}") from None


@app.get("/me")
def get_current_user(user_id: Annotated[UserId, Depends(get_user_id_from_header)]) -> User:
    ...


# Cookie validation
def get_session_user(session_user_id: Annotated[str, Cookie()]) -> UserId:
    try:
        return parse_user_id(session_user_id)
    except UPLIDError as e:
        raise HTTPException(422, f"Invalid session cookie: {e}") from None


@app.get("/session")
def get_session(user_id: Annotated[UserId, Depends(get_session_user)]) -> User:
    ...
```

## SQLAlchemy Integration

Use `uplid_column` for typed UPLID columns with automatic serialization:

```python
from typing import Literal
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from uplid import UPLID, factory
from uplid.sqlalchemy import uplid_column

UserId = UPLID[Literal["usr"]]
OrgId = UPLID[Literal["org"]]
UserIdFactory = factory(UserId)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    # Columns typed as UPLID, stored as TEXT, auto-serialized
    id: Mapped[UserId] = uplid_column(UserId, primary_key=True)
    org_id: Mapped[OrgId | None] = uplid_column(OrgId)
    name: Mapped[str] = mapped_column(String(100))


engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)

with Session(engine) as session:
    # Assign UPLID directly - no str() needed
    user = User(id=UserIdFactory(), name="Alice")
    session.add(user)
    session.commit()

    # Returns UPLID objects, not strings
    row = session.execute(select(User)).scalar_one()
    print(row.id.prefix)    # "usr"
    print(row.id.datetime)  # When the ID was created

    # Query with UPLID or string
    session.execute(select(User).where(User.id == user.id))
```

## SQLModel Integration

Use `uplid_field` for SQLModel models:

```python
from typing import Literal
from sqlmodel import SQLModel, Session, select
from sqlalchemy import create_engine
from uplid import UPLID, factory
from uplid.sqlalchemy import uplid_field

UserId = UPLID[Literal["usr"]]
UserIdFactory = factory(UserId)


class User(SQLModel, table=True):
    id: UserId = uplid_field(UserId, default_factory=UserIdFactory, primary_key=True)
    name: str


engine = create_engine("sqlite:///:memory:")
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    user = User(name="Alice")
    session.add(user)
    session.commit()

    # Pydantic serialization works
    print(user.model_dump())  # {"id": "usr_...", "name": "Alice"}

    # Database queries return UPLID objects
    row = session.exec(select(User)).first()
    print(row.id.prefix)  # "usr"
```

## Prefix Rules

Prefixes must be snake_case:
- Lowercase letters and single underscores only
- Cannot start or end with underscore
- Maximum 64 characters
- Examples: `usr`, `api_key`, `org_member`

## API Reference

### `UPLID[PREFIX]`

Generic class for prefixed IDs.

```python
# Generate new ID
uid = UPLID.generate("usr")

# Parse from string
uid = UPLID.from_string("usr_0M3xL9kQ7vR2nP5wY1jZ4c", "usr")

# Properties
uid.prefix      # str: "usr"
uid.uid         # UUID: underlying UUIDv7
uid.base62_uid  # str: 22-char base62 encoding
uid.datetime    # datetime: UTC timestamp from UUIDv7
uid.timestamp   # float: Unix timestamp in seconds
```

### `factory(UPLIDType)`

Creates a factory function for Pydantic's `default_factory`.

```python
UserId = UPLID[Literal["usr"]]
UserIdFactory = factory(UserId)

class User(BaseModel):
    id: UserId = Field(default_factory=UserIdFactory)
```

### `parse(UPLIDType)`

Creates a parser function that raises `UPLIDError` on invalid input.

```python
from uplid import UPLID, parse, UPLIDError

UserId = UPLID[Literal["usr"]]
parse_user_id = parse(UserId)

try:
    uid = parse_user_id("usr_0M3xL9kQ7vR2nP5wY1jZ4c")
except UPLIDError as e:
    print(e)
```

### `UPLIDType`

Protocol for generic functions accepting any UPLID:

```python
from uplid import UPLIDType

def log_entity(id: UPLIDType) -> None:
    print(f"{id.prefix} created at {id.datetime}")
```

### `UPLIDError`

Exception raised for invalid IDs. Subclasses `ValueError`.

### `uplid_column(UPLIDType, **kwargs)` (from `uplid.sqlalchemy`)

Creates a SQLAlchemy `mapped_column` for a UPLID type with automatic serialization.

```python
from uplid.sqlalchemy import uplid_column

UserId = UPLID[Literal["usr"]]

class User(Base):
    id: Mapped[UserId] = uplid_column(UserId, primary_key=True)
```

### `uplid_field(UPLIDType, **kwargs)` (from `uplid.sqlalchemy`)

Creates a SQLModel `Field` for a UPLID type with automatic serialization.

```python
from uplid.sqlalchemy import uplid_field

UserId = UPLID[Literal["usr"]]

class User(SQLModel, table=True):
    id: UserId = uplid_field(UserId, default_factory=UserIdFactory, primary_key=True)
```

## License

MIT
