# UPLID

Universal Prefixed Literal IDs - type-safe, human-readable identifiers for Python 3.14+.

[![CI](https://github.com/zvsdev/uplid/actions/workflows/ci.yml/badge.svg)](https://github.com/zvsdev/uplid/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/uplid)](https://pypi.org/project/uplid/)
[![Python](https://img.shields.io/pypi/pyversions/uplid)](https://pypi.org/project/uplid/)

## Features

- **Type-safe prefixes**: `UPLID[Literal["usr"]]` prevents mixing user IDs with org IDs at compile time
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

# Type safety - these are compile-time errors:
# user.org_id = user_id  # Error: UserId is not compatible with OrgId
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

## Database Storage

UPLIDs serialize to strings. Store as `VARCHAR(87)` (64 char prefix + 1 underscore + 22 char base62):

```python
from typing import Literal
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from uplid import UPLID, factory

UserId = UPLID[Literal["usr"]]
UserIdFactory = factory(UserId)


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(87), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


# Create with UPLID, store as string
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)

with Session(engine) as session:
    user = UserRow(id=str(UPLID.generate("usr")), name="Alice")
    session.add(user)
    session.commit()

    # Query and parse back to UPLID
    row = session.query(UserRow).first()
    user_id = UPLID.from_string(row.id, "usr")
    print(user_id.datetime)  # When the ID was created
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

## License

MIT
