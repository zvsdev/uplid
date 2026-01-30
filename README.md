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

# Define typed ID aliases
UserId = UPLID[Literal["usr"]]
OrgId = UPLID[Literal["org"]]

# Use in Pydantic models
class User(BaseModel):
    id: UserId = Field(default_factory=factory(UserId))
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

## FastAPI Integration

```python
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from uplid import UPLID, factory, parse, UPLIDError

UserId = UPLID[Literal["usr"]]
parse_user_id = parse(UserId)

class User(BaseModel):
    id: UserId = Field(default_factory=factory(UserId))
    name: str

app = FastAPI()
users: dict[str, User] = {}

@app.post("/users")
def create_user(name: str) -> User:
    user = User(name=name)
    users[str(user.id)] = user
    return user

@app.get("/users/{user_id}")
def get_user(user_id: str) -> User:
    try:
        parsed = parse_user_id(user_id)
    except UPLIDError:
        raise HTTPException(400, "Invalid user ID format")
    if str(parsed) not in users:
        raise HTTPException(404, "User not found")
    return users[str(parsed)]
```

## Database Storage

UPLIDs serialize to strings. Store as `VARCHAR(87)` (64 char prefix + 1 underscore + 22 char base62):

```python
# SQLAlchemy
from sqlalchemy import String
from sqlalchemy.orm import mapped_column

class User(Base):
    id: Mapped[str] = mapped_column(String(87), primary_key=True)

# Create with UPLID, store as string
user = User(id=str(UPLID.generate("usr")))
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
uid.prefix      # "usr"
uid.uid         # UUID object (UUIDv7)
uid.datetime    # datetime (UTC) from UUIDv7 timestamp
uid.timestamp   # float (Unix timestamp in seconds)
uid.base62_uid  # "0M3xL9kQ7vR2nP5wY1jZ4c" (22 chars)
```

### `factory(UPLIDType)`

Creates a factory function for Pydantic's `default_factory`.

```python
UserId = UPLID[Literal["usr"]]

class User(BaseModel):
    id: UserId = Field(default_factory=factory(UserId))
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
