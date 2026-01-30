# UPLID

Universal Prefixed Literal IDs - type-safe, human-readable identifiers for Python 3.14+.

[![CI](https://github.com/zvsdev/uplid/actions/workflows/ci.yml/badge.svg)](https://github.com/zvsdev/uplid/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/uplid)](https://pypi.org/project/uplid/)
[![Python](https://img.shields.io/pypi/pyversions/uplid)](https://pypi.org/project/uplid/)

## Features

- **Type-safe prefixes**: `UPLID[Literal["usr"]]` prevents mixing user IDs with org IDs
- **Human-readable**: `usr_4mJ9k2L8nP3qR7sT1vW5xY` (Stripe-style)
- **Time-sortable**: Built on UUIDv7 for natural ordering
- **Compact**: 22-character base62 encoding
- **Zero external deps**: Uses Python 3.14's stdlib `uuid7()`
- **Pydantic 2 native**: Full validation and serialization support

## Installation

```bash
pip install uplid
# or
uv add uplid
```

Requires Python 3.14+.

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
print(user_id)  # usr_4mJ9k2L8nP3qR7sT1vW5xY

# Parse from string
parsed = UPLID.from_string("usr_4mJ9k2L8nP3qR7sT1vW5xY", "usr")

# Type safety - these are compile-time errors with ty/mypy:
# user.org_id = user_id  # Error: UserId != OrgId
```

## Prefix Rules

Prefixes must be snake_case:
- Lowercase letters and underscores only
- Cannot start or end with underscore
- Examples: `usr`, `api_key`, `org_member`

## API Reference

### `UPLID[PREFIX]`

Generic class for prefixed IDs.

```python
# Generate new ID
uid = UPLID.generate("usr")

# Parse from string
uid = UPLID.from_string("usr_abc123...", "usr")

# Properties
uid.prefix      # "usr"
uid.uid         # UUID object
uid.datetime    # datetime from UUIDv7
uid.timestamp   # float (Unix timestamp)
uid.base62_uid  # "abc123..." (22 chars)
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
    uid = parse_user_id("usr_abc123...")
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

```python
from uplid import UPLIDError

try:
    UPLID.from_string("invalid", "usr")
except UPLIDError as e:
    print(e)
except ValueError:  # Also works
    pass
```

## License

MIT
