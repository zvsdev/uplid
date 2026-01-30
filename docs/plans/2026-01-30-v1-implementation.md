# UPLID v1.0 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Modernize UPLID to use Python 3.14's stdlib UUIDv7 with base62 encoding, eliminating external dependencies.

**Architecture:** Single module (`src/uplid/uplid.py`) with `UPLID` generic class, `UPLIDType` protocol, `UPLIDError` exception, and `factory`/`validator` helpers. Pydantic integration via `__get_pydantic_core_schema__`. Base62 encoding converts 128-bit UUIDv7 to 22-character strings.

**Tech Stack:** Python 3.14+, pydantic 2.10+, pytest, hypothesis, uv, ty, ruff

---

## Task 1: Project Structure Setup

**Files:**
- Delete: `uplid/uplid.py`, `uplid/__init__.py`, `uplid/py.typed`, `tests.py`, `example.py`, `scripts/`, `.tool-versions`, `.vscode/`
- Create: `src/uplid/__init__.py`, `src/uplid/uplid.py`, `src/uplid/py.typed`
- Create: `tests/__init__.py`, `tests/conftest.py`
- Replace: `pyproject.toml`
- Replace: `.github/workflows/ci.yml`
- Create: `.github/dependabot.yml`

**Step 1: Delete old files**

```bash
rm -rf uplid/ tests.py example.py scripts/ .tool-versions .vscode/
```

**Step 2: Create new directory structure**

```bash
mkdir -p src/uplid tests .github/workflows
touch src/uplid/py.typed tests/__init__.py
```

**Step 3: Create pyproject.toml**

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

**Step 4: Create CI workflow**

```yaml
# .github/workflows/ci.yml
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

**Step 5: Create Dependabot config**

```yaml
# .github/dependabot.yml
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

**Step 6: Install dependencies**

```bash
uv sync
```

Expected: Virtual environment created, all dev dependencies installed.

**Step 7: Verify tooling works**

```bash
uv run ruff check src/ tests/
uv run ty check
uv run pytest
```

Expected: All pass (no files to check yet, 0 tests collected).

**Step 8: Commit**

```bash
git add -A
git commit -m "chore: set up project structure with uv, ty, ruff

- Replace poetry with uv_build
- Add comprehensive ruff lint rules
- Add ty for type checking
- Add CI workflow with trusted publishing
- Add Dependabot with 3-day cooldown"
```

---

## Task 2: Base62 Encoding

**Files:**
- Create: `src/uplid/uplid.py`
- Create: `tests/test_base62.py`

**Step 1: Write failing tests for base62**

```python
# tests/test_base62.py
from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st


class TestBase62Encoding:
    def test_zero_encodes_to_padded_zeros(self) -> None:
        from uplid.uplid import _int_to_base62

        assert _int_to_base62(0) == "0" * 22

    def test_max_uuid_fits_in_22_chars(self) -> None:
        from uplid.uplid import _int_to_base62

        max_128_bit = (1 << 128) - 1
        result = _int_to_base62(max_128_bit)
        assert len(result) == 22

    def test_roundtrip_preserves_value(self) -> None:
        from uplid.uplid import _base62_to_int, _int_to_base62

        original = 12345678901234567890
        encoded = _int_to_base62(original)
        decoded = _base62_to_int(encoded)
        assert decoded == original

    @given(st.integers(min_value=0, max_value=(1 << 128) - 1))
    def test_roundtrip_any_128bit_int(self, num: int) -> None:
        from uplid.uplid import _base62_to_int, _int_to_base62

        encoded = _int_to_base62(num)
        assert len(encoded) == 22
        decoded = _base62_to_int(encoded)
        assert decoded == num

    def test_invalid_char_raises(self) -> None:
        from uplid.uplid import _base62_to_int

        with pytest.raises(KeyError):
            _base62_to_int("invalid!")
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_base62.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'uplid'` or `ImportError`.

**Step 3: Write base62 implementation**

```python
# src/uplid/uplid.py
"""Universal Prefixed Literal IDs - type-safe, human-readable identifiers."""

from __future__ import annotations

_BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_BASE62_MAP = {c: i for i, c in enumerate(_BASE62)}


def _int_to_base62(num: int) -> str:
    """Convert integer to base62 string, padded to 22 chars for UUIDv7."""
    if num == 0:
        return "0" * 22

    result: list[str] = []
    while num > 0:
        num, remainder = divmod(num, 62)
        result.append(_BASE62[remainder])

    return "".join(reversed(result)).zfill(22)


def _base62_to_int(s: str) -> int:
    """Convert base62 string to integer."""
    result = 0
    for char in s:
        result = result * 62 + _BASE62_MAP[char]
    return result
```

**Step 4: Create minimal __init__.py**

```python
# src/uplid/__init__.py
"""Universal Prefixed Literal IDs - type-safe, human-readable identifiers."""

from __future__ import annotations
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_base62.py -v
```

Expected: All 5 tests PASS.

**Step 6: Run linting and type checking**

```bash
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/
uv run ty check
```

Expected: All pass.

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: add base62 encoding for UUIDv7

- 22-char encoding for 128-bit integers
- O(1) decoding via lookup table
- Property-based tests with hypothesis"
```

---

## Task 3: UPLIDError and UPLIDType

**Files:**
- Modify: `src/uplid/uplid.py`
- Create: `tests/test_types.py`

**Step 1: Write failing tests**

```python
# tests/test_types.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from uplid import UPLIDType


class TestUPLIDError:
    def test_is_value_error_subclass(self) -> None:
        from uplid import UPLIDError

        assert issubclass(UPLIDError, ValueError)

    def test_can_catch_as_value_error(self) -> None:
        from uplid import UPLIDError

        try:
            raise UPLIDError("test message")
        except ValueError as e:
            assert str(e) == "test message"


class TestUPLIDTypeProtocol:
    def test_protocol_has_required_attributes(self) -> None:
        from uplid import UPLIDType

        assert hasattr(UPLIDType, "prefix")
        assert hasattr(UPLIDType, "uid")
        assert hasattr(UPLIDType, "datetime")

    def test_protocol_is_runtime_checkable(self) -> None:
        from typing import runtime_checkable

        from uplid import UPLIDType

        # Protocol should have @runtime_checkable decorator
        assert hasattr(UPLIDType, "__protocol_attrs__") or hasattr(
            UPLIDType, "_is_runtime_protocol"
        )
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_types.py -v
```

Expected: FAIL with `ImportError: cannot import name 'UPLIDError' from 'uplid'`.

**Step 3: Implement UPLIDError and UPLIDType**

Add to `src/uplid/uplid.py`:

```python
# Add imports at top
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID


class UPLIDError(ValueError):
    """Raised when UPLID parsing or validation fails."""


@runtime_checkable
class UPLIDType(Protocol):
    """Protocol for any UPLID, useful for generic function signatures."""

    @property
    def prefix(self) -> str:
        """The prefix identifier (e.g., 'usr', 'api_key')."""
        ...

    @property
    def uid(self) -> UUID:
        """The underlying UUIDv7."""
        ...

    @property
    def datetime(self) -> datetime:
        """The timestamp extracted from the UUIDv7."""
        ...

    def __str__(self) -> str:
        """String representation as '<prefix>_<base62uid>'."""
        ...
```

**Step 4: Update __init__.py exports**

```python
# src/uplid/__init__.py
"""Universal Prefixed Literal IDs - type-safe, human-readable identifiers."""

from __future__ import annotations

from uplid.uplid import UPLIDError, UPLIDType

__all__ = ["UPLIDError", "UPLIDType"]
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_types.py -v
```

Expected: All 4 tests PASS.

**Step 6: Run linting and type checking**

```bash
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/
uv run ty check
```

Expected: All pass.

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: add UPLIDError exception and UPLIDType protocol

- UPLIDError subclasses ValueError for easy catching
- UPLIDType protocol enables generic function signatures"
```

---

## Task 4: UPLID Core Class

**Files:**
- Modify: `src/uplid/uplid.py`
- Create: `tests/test_uplid_core.py`

**Step 1: Write failing tests for core functionality**

```python
# tests/test_uplid_core.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st


UserId = "UPLID[Literal['usr']]"  # Type alias placeholder


class TestUPLIDGeneration:
    def test_generate_creates_valid_uplid(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        assert uid.prefix == "usr"
        assert isinstance(uid.uid, UUID)

    def test_generate_with_timestamp(self) -> None:
        from uplid import UPLID

        ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        uid = UPLID.generate("usr", at=ts)
        # Timestamp should be within 1 second (ms precision)
        assert abs(uid.datetime.timestamp() - ts.timestamp()) < 1

    def test_generate_rejects_uppercase_prefix(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="snake_case"):
            UPLID.generate("USR")

    def test_generate_rejects_prefix_starting_with_underscore(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="snake_case"):
            UPLID.generate("_usr")

    def test_generate_rejects_prefix_ending_with_underscore(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="snake_case"):
            UPLID.generate("usr_")

    def test_generate_accepts_snake_case_prefix(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("api_key")
        assert uid.prefix == "api_key"

    def test_generate_accepts_multi_underscore_prefix(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("org_member_role")
        assert uid.prefix == "org_member_role"

    def test_generate_accepts_single_char_prefix(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("x")
        assert uid.prefix == "x"


class TestUPLIDStringConversion:
    def test_str_format(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        s = str(uid)
        assert s.startswith("usr_")
        assert len(s) == 4 + 22  # prefix + underscore + base62

    def test_repr_shows_values(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        r = repr(uid)
        assert r.startswith("UPLID(")
        assert "'usr'" in r


class TestUPLIDParsing:
    def test_from_string_roundtrip(self) -> None:
        from uplid import UPLID

        original = UPLID.generate("usr")
        parsed = UPLID.from_string(str(original), "usr")
        assert original == parsed

    def test_from_string_with_underscore_prefix(self) -> None:
        from uplid import UPLID

        original = UPLID.generate("api_key")
        parsed = UPLID.from_string(str(original), "api_key")
        assert original == parsed

    def test_from_string_rejects_missing_underscore(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="format"):
            UPLID.from_string("nounderscore", "usr")

    def test_from_string_rejects_wrong_prefix(self) -> None:
        from uplid import UPLID, UPLIDError

        uid = UPLID.generate("usr")
        with pytest.raises(UPLIDError, match="Expected prefix"):
            UPLID.from_string(str(uid), "org")

    def test_from_string_rejects_invalid_uid_length(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="22 characters"):
            UPLID.from_string("usr_tooshort", "usr")

    def test_from_string_rejects_invalid_base62(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="Invalid base62"):
            UPLID.from_string("usr_!!!!!!!!!!!!!!!!!!!!!!", "usr")


class TestUPLIDProperties:
    def test_datetime_property(self) -> None:
        from uplid import UPLID

        before = datetime.now(timezone.utc)
        uid = UPLID.generate("usr")
        after = datetime.now(timezone.utc)

        assert before <= uid.datetime <= after

    def test_timestamp_property(self) -> None:
        from uplid import UPLID

        before = datetime.now(timezone.utc).timestamp()
        uid = UPLID.generate("usr")
        after = datetime.now(timezone.utc).timestamp()

        assert before <= uid.timestamp <= after

    def test_base62_uid_is_cached(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        first = uid.base62_uid
        second = uid.base62_uid
        assert first is second  # Same object, not just equal
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_uplid_core.py -v
```

Expected: FAIL with `ImportError: cannot import name 'UPLID' from 'uplid'`.

**Step 3: Implement UPLID class**

Add to `src/uplid/uplid.py`:

```python
# Add imports at top
import os
import re
from datetime import timezone
from typing import Any, LiteralString, Self
from uuid import uuid7

PREFIX_PATTERN = re.compile(r"^[a-z]([a-z_]*[a-z])?$")


class UPLID[PREFIX: LiteralString]:
    """Universal Prefixed Literal ID with type-safe prefix validation.

    A UPLID combines a string prefix (like 'usr', 'api_key') with a UUIDv7,
    encoded in base62 for compactness. The prefix enables runtime and static
    type checking to prevent mixing IDs from different domains.

    Example:
        >>> UserId = UPLID[Literal["usr"]]
        >>> user_id = UPLID.generate("usr")
        >>> print(user_id)  # usr_4mJ9k2L8nP3qR7sT1vW5xY
    """

    __slots__ = ("prefix", "uid", "_base62_uid")

    prefix: PREFIX
    uid: UUID
    _base62_uid: str | None

    def __init__(self, prefix: PREFIX, uid: UUID) -> None:
        """Initialize a UPLID with a prefix and UUID.

        Args:
            prefix: The string prefix (must be snake_case).
            uid: The UUIDv7 instance.
        """
        self.prefix = prefix
        self.uid = uid
        self._base62_uid = None

    @property
    def base62_uid(self) -> str:
        """The base62-encoded UID (22 characters)."""
        if self._base62_uid is None:
            self._base62_uid = _int_to_base62(self.uid.int)
        return self._base62_uid

    @property
    def datetime(self) -> datetime:
        """The timestamp extracted from the UUIDv7."""
        ms = self.uid.int >> 80
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)

    @property
    def timestamp(self) -> float:
        """The Unix timestamp (seconds) from the UUIDv7."""
        ms = self.uid.int >> 80
        return ms / 1000

    def __str__(self) -> str:
        """Return the string representation as '<prefix>_<base62uid>'."""
        return f"{self.prefix}_{self.base62_uid}"

    def __repr__(self) -> str:
        """Return a detailed representation."""
        return f"UPLID({self.prefix!r}, {self.base62_uid!r})"

    def __hash__(self) -> int:
        """Return hash for use in sets and dict keys."""
        return hash((self.prefix, self.uid))

    def __eq__(self, other: object) -> bool:
        """Check equality with another UPLID."""
        if isinstance(other, UPLID):
            return self.prefix == other.prefix and self.uid == other.uid
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) < (other.prefix, other.uid)
        return NotImplemented

    def __le__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) <= (other.prefix, other.uid)
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) > (other.prefix, other.uid)
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        """Compare for sorting (by prefix, then by uid)."""
        if isinstance(other, UPLID):
            return (self.prefix, self.uid) >= (other.prefix, other.uid)
        return NotImplemented

    @classmethod
    def generate(cls, prefix: PREFIX, at: datetime | None = None) -> Self:
        """Generate a new UPLID with the given prefix.

        Args:
            prefix: The string prefix (must be snake_case: lowercase letters
                and underscores, cannot start/end with underscore).
            at: Optional timestamp for the UUIDv7. If None, uses current time.

        Returns:
            A new UPLID instance.

        Raises:
            UPLIDError: If the prefix is not valid snake_case.
        """
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
        """Parse a UPLID from its string representation.

        Args:
            string: The string to parse (format: '<prefix>_<base62uid>').
            prefix: The expected prefix.

        Returns:
            A UPLID instance.

        Raises:
            UPLIDError: If the string format is invalid or prefix doesn't match.
        """
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
```

**Step 4: Update __init__.py exports**

```python
# src/uplid/__init__.py
"""Universal Prefixed Literal IDs - type-safe, human-readable identifiers."""

from __future__ import annotations

from uplid.uplid import UPLID, UPLIDError, UPLIDType

__all__ = ["UPLID", "UPLIDError", "UPLIDType"]
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_uplid_core.py -v
```

Expected: All tests PASS.

**Step 6: Run linting and type checking**

```bash
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/
uv run ty check
```

Expected: All pass.

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: implement UPLID core class

- UUIDv7-based with base62 encoding (22 chars)
- Snake_case prefix validation
- Custom timestamp support
- Full comparison operators
- Lazy base62_uid caching with __slots__"
```

---

## Task 5: UPLID Equality, Hashing, and Ordering

**Files:**
- Create: `tests/test_uplid_comparison.py`

**Step 1: Write tests for comparison behavior**

```python
# tests/test_uplid_comparison.py
from __future__ import annotations

import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


prefix_strategy = st.from_regex(r"[a-z]([a-z_]*[a-z])?", fullmatch=True).filter(
    lambda s: "__" not in s and len(s) <= 20
)


class TestUPLIDEquality:
    def test_equal_uplids_are_equal(self) -> None:
        from uplid import UPLID

        uid1 = UPLID.generate("usr")
        uid2 = UPLID.from_string(str(uid1), "usr")
        assert uid1 == uid2

    def test_different_prefixes_not_equal(self) -> None:
        from uuid import uuid7

        from uplid import UPLID

        # Same UUID, different prefix
        u = uuid7()
        uid1 = UPLID("usr", u)
        uid2 = UPLID("org", u)
        assert uid1 != uid2

    def test_different_uuids_not_equal(self) -> None:
        from uplid import UPLID

        uid1 = UPLID.generate("usr")
        uid2 = UPLID.generate("usr")
        assert uid1 != uid2

    def test_not_equal_to_string(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        assert uid != str(uid)

    def test_not_equal_to_none(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        assert uid != None  # noqa: E711

    @given(prefix_strategy)
    def test_equality_is_reflexive(self, prefix: str) -> None:
        from uplid import UPLID

        uid = UPLID.generate(prefix)
        assert uid == uid


class TestUPLIDHashing:
    def test_equal_uplids_have_equal_hashes(self) -> None:
        from uplid import UPLID

        uid1 = UPLID.generate("usr")
        uid2 = UPLID.from_string(str(uid1), "usr")
        assert hash(uid1) == hash(uid2)

    def test_can_use_as_dict_key(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        d = {uid: "value"}
        assert d[uid] == "value"

    def test_can_use_in_set(self) -> None:
        from uplid import UPLID

        uid1 = UPLID.generate("usr")
        uid2 = UPLID.from_string(str(uid1), "usr")
        uid3 = UPLID.generate("usr")

        s = {uid1, uid2, uid3}
        assert len(s) == 2  # uid1 and uid2 are equal


class TestUPLIDOrdering:
    def test_sorts_by_timestamp(self) -> None:
        from uplid import UPLID

        first = UPLID.generate("usr")
        time.sleep(0.002)  # Ensure different ms timestamp
        second = UPLID.generate("usr")
        time.sleep(0.002)
        third = UPLID.generate("usr")

        assert first < second < third
        assert sorted([third, first, second]) == [first, second, third]

    def test_sorts_by_prefix_first(self) -> None:
        from uplid import UPLID

        a = UPLID.generate("aaa")
        z = UPLID.generate("zzz")
        assert a < z

    def test_comparison_with_non_uplid_returns_not_implemented(self) -> None:
        from uplid import UPLID

        uid = UPLID.generate("usr")
        assert uid.__lt__("string") == NotImplemented
        assert uid.__le__("string") == NotImplemented
        assert uid.__gt__("string") == NotImplemented
        assert uid.__ge__("string") == NotImplemented

    @given(st.lists(prefix_strategy, min_size=2, max_size=5))
    @settings(max_examples=20)
    def test_ordering_is_consistent(self, prefixes: list[str]) -> None:
        from uplid import UPLID

        ids = [UPLID.generate(p) for p in prefixes]
        assert sorted(sorted(ids)) == sorted(ids)
```

**Step 2: Run tests to verify they pass**

```bash
uv run pytest tests/test_uplid_comparison.py -v
```

Expected: All tests PASS (functionality already implemented).

**Step 3: Run full test suite**

```bash
uv run pytest -v
```

Expected: All tests pass.

**Step 4: Commit**

```bash
git add -A
git commit -m "test: add comprehensive equality, hashing, and ordering tests

- Hypothesis property tests for consistency
- Dict/set usage tests
- Cross-type comparison behavior"
```

---

## Task 6: Pydantic Integration

**Files:**
- Modify: `src/uplid/uplid.py`
- Create: `tests/test_pydantic.py`

**Step 1: Write failing tests for Pydantic integration**

```python
# tests/test_pydantic.py
from __future__ import annotations

from typing import Literal

import pytest
from pydantic import BaseModel, Field, ValidationError


class TestPydanticValidation:
    def test_validates_from_string(self) -> None:
        from uplid import UPLID, factory

        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId

        uid = UPLID.generate("usr")
        user = User(id=str(uid))
        assert user.id == uid

    def test_validates_from_uplid(self) -> None:
        from uplid import UPLID, factory

        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId

        uid = UPLID.generate("usr")
        user = User(id=uid)
        assert user.id == uid

    def test_rejects_wrong_prefix(self) -> None:
        from uplid import UPLID

        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId

        org_id = UPLID.generate("org")
        with pytest.raises(ValidationError):
            User(id=org_id)

    def test_rejects_wrong_prefix_string(self) -> None:
        from uplid import UPLID

        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId

        org_id = UPLID.generate("org")
        with pytest.raises(ValidationError):
            User(id=str(org_id))

    def test_rejects_invalid_string(self) -> None:
        from uplid import UPLID

        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId

        with pytest.raises(ValidationError):
            User(id="not_a_valid_id")

    def test_works_with_default_factory(self) -> None:
        from uplid import UPLID, factory

        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))

        user = User()
        assert user.id.prefix == "usr"


class TestPydanticSerialization:
    def test_serializes_to_string_in_dict(self) -> None:
        from uplid import UPLID, factory

        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))

        user = User()
        data = user.model_dump()
        assert isinstance(data["id"], str)
        assert data["id"].startswith("usr_")

    def test_serializes_to_string_in_json(self) -> None:
        from uplid import UPLID, factory

        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))

        user = User()
        json_str = user.model_dump_json()
        assert '"usr_' in json_str

    def test_roundtrip_model_dump(self) -> None:
        from uplid import UPLID, factory

        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))

        user = User()
        data = user.model_dump()
        rehydrated = User(**data)
        assert rehydrated == user

    def test_roundtrip_json(self) -> None:
        from uplid import UPLID, factory

        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))

        user = User()
        json_str = user.model_dump_json()
        rehydrated = User.model_validate_json(json_str)
        assert rehydrated == user


class TestPydanticWithUnderscorePrefix:
    def test_validates_underscore_prefix(self) -> None:
        from uplid import UPLID, factory

        ApiKeyId = UPLID[Literal["api_key"]]

        class ApiKey(BaseModel):
            id: ApiKeyId = Field(default_factory=factory(ApiKeyId))

        key = ApiKey()
        assert key.id.prefix == "api_key"

        # Roundtrip
        data = key.model_dump()
        rehydrated = ApiKey(**data)
        assert rehydrated == key


class TestPydanticErrorMessages:
    def test_error_on_unparameterized_uplid(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError, match="parameterized"):

            class Bad(BaseModel):
                id: UPLID  # type: ignore
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_pydantic.py -v
```

Expected: FAIL with `ImportError: cannot import name 'factory' from 'uplid'`.

**Step 3: Implement Pydantic integration and helpers**

Add to `src/uplid/uplid.py`:

```python
# Add imports at top
from typing import Callable, get_args, get_origin

from pydantic import ValidationError
from pydantic_core import CoreSchema, PydanticCustomError, core_schema


# Add to UPLID class
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: Any,
    ) -> CoreSchema:
        """Pydantic integration for validation and serialization."""
        origin = get_origin(source_type)
        if origin is None:
            raise UPLIDError(
                "UPLID must be parameterized with a prefix literal, "
                "e.g. UPLID[Literal['usr']]"
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


# Add helper functions at end of file
def _get_prefix[PREFIX: LiteralString](uplid_type: type[UPLID[PREFIX]]) -> str:
    """Extract the prefix string from a parameterized UPLID type."""
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
    """Create a factory function for generating new UPLIDs of a specific type.

    Usage:
        UserId = UPLID[Literal["usr"]]

        class User(BaseModel):
            id: UserId = Field(default_factory=factory(UserId))

    Args:
        uplid_type: A parameterized UPLID type like UPLID[Literal["usr"]].

    Returns:
        A callable that generates new UPLIDs with the correct prefix.
    """
    prefix = _get_prefix(uplid_type)

    def _factory() -> UPLID[PREFIX]:
        return UPLID.generate(prefix)

    return _factory


def validator[PREFIX: LiteralString](
    uplid_type: type[UPLID[PREFIX]],
) -> Callable[[str], UPLID[PREFIX]]:
    """Create a validator function for parsing UPLIDs of a specific type.

    Usage:
        UserId = UPLID[Literal["usr"]]
        validate_user_id = validator(UserId)
        user_id = validate_user_id("usr_4mJ9k2L8nP3qR7sT1vW5xY")

    Args:
        uplid_type: A parameterized UPLID type like UPLID[Literal["usr"]].

    Returns:
        A callable that parses strings into UPLIDs with prefix validation.
    """
    prefix = _get_prefix(uplid_type)

    def _validator(v: str) -> UPLID[PREFIX]:
        try:
            return UPLID.from_string(v, prefix)
        except UPLIDError as e:
            raise ValidationError.from_exception_data(
                f"{prefix.replace('_', ' ').title().replace(' ', '')}Id",
                [
                    {
                        "loc": (f"{prefix}_id",),
                        "input": v,
                        "type": PydanticCustomError("uplid_error", str(e)),
                    }
                ],
            ) from e

    return _validator
```

**Step 4: Update __init__.py exports**

```python
# src/uplid/__init__.py
"""Universal Prefixed Literal IDs - type-safe, human-readable identifiers."""

from __future__ import annotations

from uplid.uplid import UPLID, UPLIDError, UPLIDType, factory, validator

__all__ = ["UPLID", "UPLIDError", "UPLIDType", "factory", "validator"]
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_pydantic.py -v
```

Expected: All tests PASS.

**Step 6: Run full test suite**

```bash
uv run pytest -v
```

Expected: All tests pass.

**Step 7: Run linting and type checking**

```bash
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/
uv run ty check
```

Expected: All pass.

**Step 8: Commit**

```bash
git add -A
git commit -m "feat: add Pydantic integration and helper functions

- __get_pydantic_core_schema__ for validation/serialization
- factory() for default_factory in Pydantic models
- validator() for parsing with ValidationError
- Full JSON roundtrip support"
```

---

## Task 7: Protocol Conformance Test

**Files:**
- Modify: `tests/test_types.py`

**Step 1: Add protocol conformance test**

Add to `tests/test_types.py`:

```python
class TestUPLIDConformsToProtocol:
    def test_uplid_instance_matches_protocol(self) -> None:
        from uplid import UPLID, UPLIDType

        uid = UPLID.generate("usr")
        assert isinstance(uid, UPLIDType)

    def test_protocol_allows_generic_functions(self) -> None:
        from uplid import UPLID, UPLIDType

        def get_timestamp(id: UPLIDType) -> float:
            return id.timestamp

        uid = UPLID.generate("usr")
        ts = get_timestamp(uid)
        assert ts > 0

    def test_protocol_allows_any_prefix(self) -> None:
        from uplid import UPLID, UPLIDType

        def format_id(id: UPLIDType) -> str:
            return f"[{id.prefix}] {id.datetime.isoformat()}"

        usr_id = UPLID.generate("usr")
        api_id = UPLID.generate("api_key")

        assert "[usr]" in format_id(usr_id)
        assert "[api_key]" in format_id(api_id)
```

**Step 2: Run tests to verify they pass**

```bash
uv run pytest tests/test_types.py -v
```

Expected: All tests PASS.

**Step 3: Commit**

```bash
git add -A
git commit -m "test: add protocol conformance tests

- Verify UPLID instances satisfy UPLIDType protocol
- Test generic functions accepting any UPLID"
```

---

## Task 8: Fuzz Testing

**Files:**
- Create: `tests/test_fuzz.py`

**Step 1: Write fuzz tests**

```python
# tests/test_fuzz.py
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


class TestParserFuzzing:
    @given(st.text())
    @settings(max_examples=500)
    def test_from_string_never_crashes(self, s: str) -> None:
        """Parser should raise UPLIDError, never crash."""
        from uplid import UPLID, UPLIDError

        try:
            UPLID.from_string(s, "test")
        except UPLIDError:
            pass  # Expected for invalid input

    @given(st.text())
    @settings(max_examples=500)
    def test_from_string_with_arbitrary_prefix_never_crashes(self, s: str) -> None:
        """Parser should handle any prefix gracefully."""
        from uplid import UPLID, UPLIDError

        try:
            UPLID.from_string(f"usr_{s}", "usr")
        except UPLIDError:
            pass  # Expected for invalid input

    @given(st.binary())
    @settings(max_examples=200)
    def test_base62_decoder_handles_arbitrary_bytes(self, b: bytes) -> None:
        """Base62 decoder should not crash on arbitrary input."""
        from uplid.uplid import _base62_to_int

        try:
            s = b.decode("utf-8", errors="ignore")
            _base62_to_int(s)
        except (KeyError, ValueError):
            pass  # Expected for invalid input


class TestPrefixFuzzing:
    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=500)
    def test_generate_validates_prefix(self, prefix: str) -> None:
        """Generate should validate prefix and never crash."""
        from uplid import UPLID, UPLIDError

        try:
            UPLID.generate(prefix)
        except UPLIDError:
            pass  # Expected for invalid prefix


class TestEdgeCases:
    def test_empty_string(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError):
            UPLID.from_string("", "usr")

    def test_only_underscore(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError):
            UPLID.from_string("_", "usr")

    def test_many_underscores(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError):
            UPLID.from_string("___", "usr")

    def test_unicode_in_uid(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError):
            UPLID.from_string("usr_" + "é" * 22, "usr")

    def test_null_bytes(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError):
            UPLID.from_string("usr_\x00" * 22, "usr")

    def test_very_long_input(self) -> None:
        from uplid import UPLID, UPLIDError

        with pytest.raises(UPLIDError):
            UPLID.from_string("a" * 10000, "usr")
```

**Step 2: Run fuzz tests**

```bash
uv run pytest tests/test_fuzz.py -v
```

Expected: All tests PASS.

**Step 3: Commit**

```bash
git add -A
git commit -m "test: add fuzz testing with hypothesis

- 500 examples for parser robustness
- Edge cases: empty, unicode, null bytes, long input
- Ensures no crashes on arbitrary input"
```

---

## Task 9: Full Test Suite Validation

**Files:**
- Create: `tests/conftest.py`

**Step 1: Create shared fixtures**

```python
# tests/conftest.py
from __future__ import annotations

from typing import Literal

import pytest
from hypothesis import strategies as st


# Hypothesis strategies
prefix_strategy = st.from_regex(r"[a-z]([a-z_]*[a-z])?", fullmatch=True).filter(
    lambda s: "__" not in s and len(s) <= 20
)

base62_char = st.sampled_from(
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)
base62_uid = st.text(base62_char, min_size=22, max_size=22)


@pytest.fixture
def user_id_type():
    """Return a UserId type alias."""
    from uplid import UPLID

    return UPLID[Literal["usr"]]


@pytest.fixture
def api_key_id_type():
    """Return an ApiKeyId type alias."""
    from uplid import UPLID

    return UPLID[Literal["api_key"]]
```

**Step 2: Run full test suite with coverage**

```bash
uv run pytest -v --tb=short
```

Expected: All tests pass.

**Step 3: Run all quality checks**

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check
```

Expected: All pass.

**Step 4: Commit**

```bash
git add -A
git commit -m "test: add shared fixtures and complete test suite

- Hypothesis strategies for property tests
- Shared type alias fixtures
- Full suite validation"
```

---

## Task 10: Update README

**Files:**
- Modify: `README.md`

**Step 1: Write new README**

```markdown
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
uid = UPLID.generate("usr", at=datetime.now())  # Custom timestamp

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

### `validator(UPLIDType)`

Creates a validator function that raises `ValidationError`.

```python
UserId = UPLID[Literal["usr"]]
validate = validator(UserId)

try:
    uid = validate("invalid")
except ValidationError as e:
    print(e)  # Structured Pydantic error
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
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for v1.0

- Quick start guide
- Full API reference
- Installation instructions"
```

---

## Task 11: Cleanup and Final Validation

**Step 1: Run full quality suite**

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run ty check
uv run pytest -v
```

Expected: All pass.

**Step 2: Verify package builds**

```bash
uv build
```

Expected: Creates `dist/uplid-1.0.0-py3-none-any.whl` and `.tar.gz`.

**Step 3: Verify clean git status**

```bash
git status
```

Expected: Clean working tree or only untracked `dist/`.

**Step 4: Final commit if any formatting changes**

```bash
git add -A
git commit -m "chore: final formatting and cleanup" || echo "Nothing to commit"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Project structure with uv, ty, ruff |
| 2 | Base62 encoding |
| 3 | UPLIDError and UPLIDType |
| 4 | UPLID core class |
| 5 | Equality, hashing, ordering tests |
| 6 | Pydantic integration |
| 7 | Protocol conformance |
| 8 | Fuzz testing |
| 9 | Test suite validation |
| 10 | README |
| 11 | Final validation |

After completing all tasks, the branch is ready for PR/merge.
