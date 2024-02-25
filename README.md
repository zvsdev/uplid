# UPLID - Universal Prefixed Literal Unique Id

A pydantic compatible, human friendly prefixed id.

Uses literal string types to enforce typing at both runtime (via pydantic) and during static analysis.

UIDs underneath are KSUIDs allowing them to be sorted by time of creation while still being collision resistant.

String representations are encoded with base62 keeping them url safe and human friendly.

Python 3.9 or higher and at least pydantic 2.6 are required.

## Usage

### With Pydantic

```py
from uplid import UPLID, factory
from pydantic import BaseModel, Field

UserId = UPLID[Literal["usr]]
WorkspaceId = UPLID[Literal["wrkspace"]]

class User(BaseModel):
  id: UserId = Field(default_factory=factory(UserId))
  workspace_id: WorkspaceId

user = User(workspace_id = UPLID.generate("wrkspace))

user_json = user.model_dump_json()

restored_user = User.validate_json(user_json)
```

### Standalone

```py
from uplid import UPLID

UserId = UPLID[Literal["usr]]

user_id = UPLID.generate("usr")
workspace_id = UPLID.generate("wrkspace")

def foo(bar: UserId) -> None:
  pass

foo(bar=user_id) # good
foo(bar=workspace_id) # fails static check
```

## Inspirations

- https://dev.to/stripe/designing-apis-for-humans-object-ids-3o5a
- https://pypi.org/project/django-charid-field/
- https://pypi.org/project/django-prefix-id/
- https://sudhir.io/uuids-ulids
