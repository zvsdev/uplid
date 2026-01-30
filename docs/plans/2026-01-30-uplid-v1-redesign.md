# UPLID v1.0 Redesign

**Date**: 2026-01-30
**Status**: Approved

## Overview

Modernize UPLID (Universal Prefixed Literal IDs) for Python 3.14+, eliminating external dependencies by using stdlib UUIDv7, and adopting modern tooling (uv, ty, ruff).

## Design Decisions

| Decision | Choice |
|----------|--------|
| ID format | UUIDv7 + base62 encoding (22 chars) |
| Prefix rules | Snake_case only (`[a-z]([a-z_]*[a-z])?`) |
| Separator | Final `_` (supports `api_key_abc123`) |
| Helpers | Keep `factory()` and `validator()` |
| Public API | `UPLID`, `UPLIDType`, `UPLIDError`, `factory`, `validator` |
| Exceptions | Single `UPLIDError(ValueError)` |
| Memory | `__slots__` for efficiency |
| Testing | Comprehensive with Hypothesis property tests |
| Python | 3.14+ only (uses stdlib `uuid7()`) |
| Tooling | uv + ty + ruff |

## Project Structure

```
uplid/
├── pyproject.toml
├── src/
│   └── uplid/
│       ├── __init__.py
│       ├── uplid.py
│       └── py.typed
├── tests/
│   ├── __init__.py
│   ├── test_uplid.py
│   ├── test_pydantic.py
│   └── conftest.py
├── .github/
│   ├── workflows/ci.yml
│   └── dependabot.yml
├── README.md
└── LICENSE
```

## Core Implementation

### Base62 Encoding

UUIDv7 is 128 bits. Base62 encoding requires 22 characters.

```python
_BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_BASE62_MAP = {c: i for i, c in enumerate(_BASE62)}

def _int_to_base62(num: int) -> str:
    if num == 0:
        return "0" * 22
    result: list[str] = []
    while num > 0:
        num, remainder = divmod(num, 62)
        result.append(_BASE62[remainder])
    return "".join(reversed(result)).zfill(22)

def _base62_to_int(s: str) -> int:
    result = 0
    for char in s:
        result = result * 62 + _BASE62_MAP[char]
    return result
```

### UPLID Class

```python
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Literal, LiteralString, Protocol, Self, get_args, get_origin
from uuid import UUID, uuid7

from pydantic_core import CoreSchema, core_schema

PREFIX_PATTERN = re.compile(r"^[a-z]([a-z_]*[a-z])?$")


class UPLIDError(ValueError):
    """Raised when UPLID parsing or validation fails."""


@runtime_checkable
class UPLIDType(Protocol):
    """Protocol for any UPLID, useful for generic function signatures."""

    @property
    def prefix(self) -> str: ...

    @property
    def uid(self) -> UUID: ...

    @property
    def datetime(self) -> datetime: ...

    def __str__(self) -> str: ...


class UPLID[PREFIX: LiteralString]:
    __slots__ = ("prefix", "uid", "_base62_uid")

    prefix: PREFIX
    uid: UUID
    _base62_uid: str | None

    def __init__(self, prefix: PREFIX, uid: UUID) -> None:
        self.prefix = prefix
        self.uid = uid
        self._base62_uid = None

    @property
    def base62_uid(self) -> str:
        if self._base62_uid is None:
            self._base62_uid = _int_to_base62(self.uid.int)
        return self._base62_uid

    @property
    def datetime(self) -> datetime:
        ms = self.uid.int >> 80
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)

    @property
    def timestamp(self) -> float:
        ms = self.uid.int >> 80
        return ms / 1000

    def __str__(self) -> str:
        return f"{self.prefix}_{self.base62_uid}"

    def __repr__(self) -> str:
        return f"UPLID({self.prefix!r}, {self.base62_uid!r})"

    def __hash__(self) -> int:
        return hash((self.prefix, self.uid))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UPLID):
            return self.prefix == other.prefix and self.uid == other.uid
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) < (other.prefix, other.uid)
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) <= (other.prefix, other.uid)
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) > (other.prefix, other.uid)
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) >= (other.prefix, other.uid)
        return NotImplemented

    @classmethod
    def generate(cls, prefix: PREFIX, at: datetime | None = None) -> Self:
        if not PREFIX_PATTERN.match(prefix):
            raise UPLIDError(
                f"Prefix must be snake_case (lowercase letters, underscores, "
                f"cannot start/end with underscore), got {prefix!r}"
            )
        if at is not None:
            ms = int(at.timestamp() * 1000)
            rand_bits = int.from_bytes(os.urandom(10), "big")
            uuid_int = (ms << 80) | (0x7 << 76) | (rand_bits & ((1 << 76) - 1))
            uuid_int = (uuid_int & ~(0x3 << 62)) | (0x2 << 62)
            uid = UUID(int=uuid_int)
        else:
            uid = uuid7()
        return cls(prefix, uid)

    @classmethod
    def from_string(cls, string: str, prefix: PREFIX) -> Self:
        if "_" not in string:
            raise UPLIDError(f"UPLID must be in format '<prefix>_<uid>', got {string!r}")
        last_underscore = string.rfind("_")
        parsed_prefix = string[:last_underscore]
        encoded_uid = string[last_underscore + 1 :]
        if not PREFIX_PATTERN.match(parsed_prefix):
            raise UPLIDError(f"Prefix must be snake_case, got {parsed_prefix!r}")
        if parsed_prefix != prefix:
            raise UPLIDError(f"Expected prefix {prefix!r}, got {parsed_prefix!r}")
        if len(encoded_uid) != 22:
            raise UPLIDError(f"UID must be 22 characters, got {len(encoded_uid)}")
        try:
            uid_int = _base62_to_int(encoded_uid)
            uid = UUID(int=uid_int)
        except (KeyError, ValueError) as e:
            raise UPLIDError(f"Invalid base62 UID: {encoded_uid!r}") from e
        instance = cls(prefix, uid)
        instance._base62_uid = encoded_uid
        return instance

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> CoreSchema:
        origin = get_origin(source_type)
        if origin is None:
            raise UPLIDError(
                "UPLID must be parameterized with a prefix literal, e.g. UPLID[Literal['usr']]"
            )
        args = get_args(source_type)
        if not args:
            raise UPLIDError("UPLID requires a Literal prefix type argument")
        prefix_type = args[0]
        prefix_args = get_args(prefix_type)
        if not prefix_args:
            if hasattr(prefix_type, "__value__"):
                prefix_args = get_args(prefix_type.__value__)
            if not prefix_args:
                raise UPLIDError(f"Could not extract prefix from {prefix_type}")
        prefix_str: str = prefix_args[0]

        def validate(v: UPLID[Any] | str) -> UPLID[Any]:
            if isinstance(v, str):
                return cls.from_string(v, prefix_str)
            if isinstance(v, UPLID):
                if v.prefix != prefix_str:
                    raise UPLIDError(f"Expected prefix {prefix_str!r}, got {v.prefix!r}")
                return v
            raise UPLIDError(f"Expected UPLID or str, got {type(v).__name__}")

        return core_schema.json_or_python_schema(
            json_schema=core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(validate),
            ]),
            python_schema=core_schema.no_info_plain_validator_function(validate),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )
```

### Helper Functions

```python
from typing import Callable

from pydantic import ValidationError
from pydantic_core import PydanticCustomError


def _get_prefix[PREFIX: LiteralString](uplid_type: type[UPLID[PREFIX]]) -> str:
    args = getattr(uplid_type, "__args__", None)
    if not args:
        raise UPLIDError("UPLID type must be parameterized with a Literal prefix")
    literal_type = args[0]
    literal_args = get_args(literal_type)
    if not literal_args:
        raise UPLIDError(f"Could not extract prefix from {literal_type}")
    return literal_args[0]


def factory[PREFIX: LiteralString](
    uplid_type: type[UPLID[PREFIX]],
) -> Callable[[], UPLID[PREFIX]]:
    """Create a factory function for generating new UPLIDs."""
    prefix = _get_prefix(uplid_type)

    def _factory() -> UPLID[PREFIX]:
        return UPLID.generate(prefix)

    return _factory


def validator[PREFIX: LiteralString](
    uplid_type: type[UPLID[PREFIX]],
) -> Callable[[str], UPLID[PREFIX]]:
    """Create a validator function for parsing UPLIDs."""
    prefix = _get_prefix(uplid_type)

    def _validator(v: str) -> UPLID[PREFIX]:
        try:
            return UPLID.from_string(v, prefix)
        except UPLIDError as e:
            raise ValidationError.from_exception_data(
                f"{prefix.replace('_', ' ').title().replace(' ', '')}Id",
                [{"loc": (f"{prefix}_id",), "input": v, "type": PydanticCustomError("uplid_error", str(e))}],
            ) from e

    return _validator
```

### Public API (`__init__.py`)

```python
from uplid.uplid import UPLID, UPLIDError, UPLIDType, factory, validator

__all__ = ["UPLID", "UPLIDError", "UPLIDType", "factory", "validator"]
```

## Configuration

### pyproject.toml

```toml
[project]
name = "uplid"
version = "1.0.0"
description = "Universal Prefixed Literal IDs - type-safe, human-readable identifiers"
authors = [{ name = "ZVS", email = "zvs@daswolf.dev" }]
readme = "README.md"
license = "MIT"
requires-python = ">=3.14"
dependencies = ["pydantic>=2.10"]
classifiers = [
    "Framework :: Pydantic :: 2",
    "Typing :: Typed",
    "Programming Language :: Python :: 3.14",
]

[project.urls]
Homepage = "https://github.com/zvsdev/uplid"
Repository = "https://github.com/zvsdev/uplid"

[build-system]
requires = ["uv_build>=0.9.28,<0.10"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "pytest>=9.0.2,<10",
    "hypothesis>=6.151.4,<7",
    "ty>=0.0.14,<0.1",
    "ruff>=0.14.14,<0.15",
]

[tool.ruff]
line-length = 100
target-version = "py314"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E", "W", "F", "I", "B", "S", "A", "T20", "RET", "SLF", "SLOT", "TRY", "FBT",
    "ANN", "TCH", "C4", "SIM", "ARG", "ERA", "PIE", "PERF", "FURB", "UP", "N", "Q", "RUF", "D",
]
ignore = ["D100", "D104", "D107", "ANN101", "ANN102", "TRY003"]

[tool.ruff.lint.isort]
known-first-party = ["uplid"]
known-third-party = ["pydantic", "pydantic_core"]
required-imports = ["from __future__ import annotations"]
force-single-line = false
lines-after-imports = 2

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "ANN", "D", "ARG001", "SLF001"]

[tool.ruff.format]
quote-style = "double"
docstring-code-format = true

[tool.ty]
python-version = "3.14"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### CI/CD (.github/workflows/ci.yml)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Set up Python 3.14
        run: uv python install 3.14
      - name: Install dependencies
        run: uv sync
      - name: Lint
        run: uv run ruff check --output-format=github
      - name: Format check
        run: uv run ruff format --check
      - name: Type check
        run: uv run ty check
      - name: Test
        run: uv run pytest --tb=short

  publish:
    needs: check
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Build
        run: uv build
      - name: Publish to PyPI
        run: uv publish --trusted-publishing always
```

### Dependabot (.github/dependabot.yml)

```yaml
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "daily"
    cooldown:
      default-days: 3
      semver-major-days: 3
      semver-minor-days: 3
      semver-patch-days: 3
    groups:
      minor-and-patch:
        applies-to: version-updates
        update-types:
          - "minor"
          - "patch"
    open-pull-requests-limit: 10
    commit-message:
      prefix: "deps"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "daily"
    cooldown:
      default-days: 3
    groups:
      minor-and-patch:
        applies-to: version-updates
        update-types:
          - "minor"
          - "patch"
    open-pull-requests-limit: 5
    commit-message:
      prefix: "ci"
```

## Testing Strategy

Comprehensive testing with Hypothesis property-based tests:

- **Property tests**: Round-trip parsing, ordering consistency, equality reflexivity
- **Fuzz testing**: Parser never crashes on arbitrary input
- **Pydantic integration**: Full lifecycle (validation, serialization, JSON schema)
- **Edge cases**: Empty strings, unicode, boundary values, invalid prefixes

Test classes:
- `TestGeneration`
- `TestParsing`
- `TestOrdering`
- `TestEquality`
- `TestPydanticIntegration`
- `TestProtocol`

## Implementation Tasks

1. Create project structure with `src/` layout
2. Implement `UPLIDError`, `UPLIDType` protocol
3. Implement base62 encoding functions
4. Implement `UPLID` class with all methods
5. Implement `factory()` and `validator()` helpers
6. Write `__init__.py` with public API
7. Create `pyproject.toml` with all tooling config
8. Create CI/CD pipeline
9. Create Dependabot config
10. Write comprehensive tests
11. Update README
12. Delete old files (`example.py`, `uplid/uplid.py`, `tests.py`, etc.)
