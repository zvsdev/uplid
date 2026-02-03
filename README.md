# UPLID

```
██╗   ██╗██████╗ ██╗     ██╗██████╗
██║   ██║██╔══██╗██║     ██║██╔══██╗
██║   ██║██████╔╝██║     ██║██║  ██║
██║   ██║██╔═══╝ ██║     ██║██║  ██║
╚██████╔╝██║     ███████╗██║██████╔╝
 ╚═════╝ ╚═╝     ╚══════╝╚═╝╚═════╝
```

**Stripe-style IDs for Python.**

```python
# Before: WTF is this?
"550e8400-e29b-41d4-a716-446655440000"

# After: It's a user.
"usr_0M3xL9kQ7vR2nP5wY1jZ4c"
```

[![CI](https://github.com/zvsdev/uplid/actions/workflows/ci.yml/badge.svg)](https://github.com/zvsdev/uplid/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/uplid)](https://pypi.org/project/uplid/)
[![Python](https://img.shields.io/pypi/pyversions/uplid)](https://pypi.org/project/uplid/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/zvsdev/uplid)

## Install

```bash
pip install uplid
```

Requires Python 3.14+ and Pydantic 2.10+.

## Quick Start

```python
>>> from uplid import UPLID
>>> UPLID.generate("usr")
usr_0M3xL9kQ7vR2nP5wY1jZ4c
>>> UPLID.generate("ord")
ord_7x9KmNpQrStUvWxYz012Ab
```

## Why UPLID?

**Debuggable** - See `usr_` in your logs and instantly know it's a user, not an order, not a session, not a mystery.

```
# Your logs now:
"User usr_0M3xL9kQ7vR2nP5wY1jZ4c created order ord_1a2B3c4D5e6F7g..."

# vs the nightmare:
"User 550e8400-e29b-41d4... created order 7c9e6679-7425-40de..."
```

**Type-safe** - Your type checker catches `user_id = order_id` mistakes before they hit production.

```python
UserId = UPLID[Literal["usr"]]
OrgId = UPLID[Literal["org"]]

def get_user(user_id: UserId) -> User: ...

get_user(org_id)  # Type error! Caught by mypy/pyright/ty
```

**Time-sortable** - Built on UUIDv7. Sort by ID = sort by creation time. No extra column needed.

**URL-safe** - 26 characters, no special characters, no encoding. `usr_0M3xL9kQ7vR2nP5wY1jZ4c`

**Minimal dependencies** - Just Pydantic. UUID generation uses Python 3.14's stdlib `uuid7()`.

> Inspired by Stripe's prefixed IDs (`sk_live_...`, `cus_...`, `pi_...`) - the same pattern trusted by millions of API calls daily.

## Pydantic Integration

```python
from typing import Literal
from pydantic import BaseModel, Field
from uplid import UPLID, factory

UserId = UPLID[Literal["usr"]]

class User(BaseModel):
    id: UserId = Field(default_factory=factory(UserId))
    name: str

user = User(name="Alice")
user.model_dump()  # {"id": "usr_0M3xL9kQ7vR2nP5wY1jZ4c", "name": "Alice"}

User(id="org_xxx...", name="Bad")  # ValidationError: wrong prefix
```

## FastAPI Integration

```python
from typing import Annotated, Literal
from fastapi import Depends, FastAPI, HTTPException
from uplid import UPLID, UPLIDError, parse

UserId = UPLID[Literal["usr"]]
parse_user_id = parse(UserId)

def validate_user_id(user_id: str) -> UserId:
    try:
        return parse_user_id(user_id)
    except UPLIDError as e:
        raise HTTPException(422, str(e)) from None

@app.get("/users/{user_id}")
def get_user(user_id: Annotated[UserId, Depends(validate_user_id)]) -> User:
    ...  # user_id is validated and typed
```

## SQLAlchemy Integration

```python
from uplid import UPLID, factory
from uplid.sqlalchemy import uplid_column

UserId = UPLID[Literal["usr"]]

class User(Base):
    __tablename__ = "users"
    id: Mapped[UserId] = uplid_column(UserId, primary_key=True)
    name: Mapped[str]

# Stores as TEXT, returns as UPLID objects
user = session.execute(select(User)).scalar_one()
user.id.prefix    # "usr"
user.id.datetime  # When the ID was created
```

## SQLModel Integration

```python
from uplid import UPLID, factory
from uplid.sqlalchemy import uplid_field

UserId = UPLID[Literal["usr"]]

class User(SQLModel, table=True):
    id: UserId = uplid_field(UserId, default_factory=factory(UserId), primary_key=True)
    name: str

user.model_dump()  # {"id": "usr_...", "name": "Alice"} - Pydantic just works
```

## Prefix Rules

Prefixes must be snake_case: lowercase letters and single underscores, cannot start/end with underscore, max 64 characters.

Examples: `usr`, `api_key`, `org_member`, `sk_live`

## API Reference

### `UPLID[PREFIX]`

```python
uid = UPLID.generate("usr")                              # Generate new
uid = UPLID.from_string("usr_0M3xL9kQ7vR2nP5wY1jZ4c", "usr")  # Parse

uid.prefix      # "usr"
uid.uid         # UUID object
uid.base62_uid  # "0M3xL9kQ7vR2nP5wY1jZ4c"
uid.datetime    # When created (from UUIDv7)
uid.timestamp   # Unix timestamp
```

### `factory(UPLIDType)` / `parse(UPLIDType)`

```python
UserId = UPLID[Literal["usr"]]
UserIdFactory = factory(UserId)  # For Pydantic default_factory
parse_user_id = parse(UserId)    # For manual parsing, raises UPLIDError
```

### `UPLIDType`

Protocol for functions accepting any UPLID:

```python
def log_entity(id: UPLIDType) -> None:
    print(f"{id.prefix} created at {id.datetime}")
```

### `uplid_column` / `uplid_field`

```python
from uplid.sqlalchemy import uplid_column, uplid_field

# SQLAlchemy
id: Mapped[UserId] = uplid_column(UserId, primary_key=True)

# SQLModel
id: UserId = uplid_field(UserId, default_factory=factory(UserId), primary_key=True)
```

## License

MIT
