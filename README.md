# LPID - Literal Prefixed Unique Ids

A pydantic compatible, human friendly prefixed id.

Uses Literal string types to enforce typing at both runtime (via pydantic) and during static analysis.

UIDs underneath are KSUIDs letting the ids be "loosely" monotonic

String representations are encoded with base62 keeping them url safe and relatively human friendly.

## Usage

### With Pydantic

```py
UserId = LPID[Literal["usr]]
WorkspaceId = LPID[Literal["wrkspace"]]

class User(BaseModel):
  id: UserId = Field(default_factory=LPID.factory("usr"))
  workspace_id: WorkspaceId
```

Supports serializing to and from dicts/json

```py
user = User(workspace_id = LPID.generate("wrkspace))

user_json = user.model_dump_json()

restored_user = User.validate_json(user_json)
```

### Standalone

```py
UserId = LPID[Literal["usr]]

user_id = LPID.generate("usr")

def foo(bar: UserId) -> None:
  ...
```
