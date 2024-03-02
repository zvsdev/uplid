# UPLID - Universal Prefixed Literal Unique Id

A pydantic compatible, human friendly prefixed id.

Uses literal string types to enforce typing at both runtime (via pydantic) and during static analysis.

UIDs underneath are KSUIDs allowing them to be sorted by time of creation while still being collision resistant.

String representations are encoded with base62 keeping them url safe and human friendly.

Python 3.9 or higher and at least pydantic 2.6 are required.

Can be integrated with FastAPI.

## Installation

```
pip install uplid
```

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
from uplid import UPLID, validator, factory

UserId = UPLID[Literal["usr]]
WorkspaceId = UPLID[Literal['wrkspace']]

UserIdFactory = factory(UserId)
WorkspaceIdFactory = factory(WorkspaceId)

user_id = UserIdFactory()
workspace_id = WorkspaceIdFactory()

def foo(bar: UserId) -> None:
  pass

foo(bar=user_id) # passes static check
foo(bar=workspace_id) # fails static check

UserIdValidator = validator(UserId)

UserIdValidator(str(workspace_id)) # fails runtime check
```

### With FastAPI

#### As a Query or Path Param

```py
from uplid import UPLID, validator
from fastapi import Request, Response, Depends

UserId = UPLID[Literal["usr]]

async def endpoint(request: Request, user_id: UserId = Depends(validator(UserId))) -> Response:
  ...
```

FastAPI depends does not convert pydantic's ValidationError to RequestValidationError if thrown inside of Depends.
As a workaround, you can add a global catch at the top level, or wrap your own handler around the UPLID validator.

```py
from fastapi import Request, FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

def handle_validation_error(request: Request, exc: Exception):
  if isinstance(exc, ValidationError):
    raise RequestValidationError(errors=exc.errors())
  raise exc

app = FastAPI()
app.add_exception_handler(ValidationError, handle_validation_error)
```

#### As part of a Body

```py
from uplid import UPLID
from fastapi import Request, Response
from pydantic import BaseModel

class UserRequest(BaseModel):
  user_id: UserId

async def endpoint(request: Request, body: UserRequest) -> Response:
  ...
```

## Inspirations

- https://dev.to/stripe/designing-apis-for-humans-object-ids-3o5a
- https://pypi.org/project/django-charid-field/
- https://pypi.org/project/django-prefix-id/
- https://sudhir.io/uuids-ulids
