from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from uplid import UPLID, UPLIDError, factory, parse


UserId = UPLID[Literal["usr"]]
OrgId = UPLID[Literal["org"]]
UserIdFactory = factory(UserId)
parse_user_id = parse(UserId)
parse_org_id = parse(OrgId)


class User(BaseModel):
    id: UserId = Field(default_factory=UserIdFactory)
    name: str
    org_id: OrgId | None = None


app = FastAPI()
users: dict[str, User] = {}


# Dependency for validating path/query params
def get_user_id(user_id: str) -> UserId:
    try:
        return parse_user_id(user_id)
    except UPLIDError as e:
        raise HTTPException(422, f"Invalid user ID: {e}") from None


def get_org_id(org_id: str) -> OrgId:
    try:
        return parse_org_id(org_id)
    except UPLIDError as e:
        raise HTTPException(422, f"Invalid org ID: {e}") from None


@app.post("/users")
def create_user(name: str, org_id: str | None = None) -> User:
    parsed_org_id = None
    if org_id:
        try:
            parsed_org_id = parse_org_id(org_id)
        except UPLIDError as e:
            raise HTTPException(422, f"Invalid org ID: {e}") from None
    user = User(name=name, org_id=parsed_org_id)
    users[str(user.id)] = user
    return user


@app.get("/users/{user_id}")
def get_user(user_id: Annotated[UserId, Depends(get_user_id)]) -> User:
    if str(user_id) not in users:
        raise HTTPException(404, "User not found")
    return users[str(user_id)]


@app.get("/users")
def list_users(org_id: Annotated[str | None, Query()] = None) -> list[User]:
    if org_id is None:
        return list(users.values())
    try:
        parsed_org_id = parse_org_id(org_id)
    except UPLIDError as e:
        raise HTTPException(422, f"Invalid org ID: {e}") from None
    return [u for u in users.values() if u.org_id == parsed_org_id]


client = TestClient(app)


class TestFastAPIPathParams:
    def setup_method(self) -> None:
        users.clear()

    def test_valid_user_id_in_path(self) -> None:
        # Create a user first
        response = client.post("/users?name=Alice")
        assert response.status_code == 200
        user_id = response.json()["id"]

        # Fetch by ID
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Alice"

    def test_invalid_user_id_format_returns_422(self) -> None:
        response = client.get("/users/not_a_valid_id")
        assert response.status_code == 422

    def test_wrong_prefix_returns_422(self) -> None:
        org_id = UPLID.generate("org")
        response = client.get(f"/users/{org_id}")
        assert response.status_code == 422

    def test_user_not_found_returns_404(self) -> None:
        valid_but_nonexistent = UPLID.generate("usr")
        response = client.get(f"/users/{valid_but_nonexistent}")
        assert response.status_code == 404


class TestFastAPIQueryParams:
    def setup_method(self) -> None:
        users.clear()

    def test_filter_by_org_id(self) -> None:
        org1 = UPLID.generate("org")
        org2 = UPLID.generate("org")

        # Create users in different orgs
        client.post(f"/users?name=Alice&org_id={org1}")
        client.post(f"/users?name=Bob&org_id={org1}")
        client.post(f"/users?name=Charlie&org_id={org2}")

        # Filter by org1
        response = client.get(f"/users?org_id={org1}")
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Filter by org2
        response = client.get(f"/users?org_id={org2}")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_invalid_org_id_returns_422(self) -> None:
        response = client.get("/users?org_id=invalid")
        assert response.status_code == 422


class TestFastAPIRequestBody:
    def setup_method(self) -> None:
        users.clear()

    def test_user_creation_generates_id(self) -> None:
        response = client.post("/users?name=Alice")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Alice"
        assert data["id"].startswith("usr_")
        assert len(data["id"]) == 26  # usr_ + 22 chars

    def test_user_serializes_to_string_id(self) -> None:
        response = client.post("/users?name=Bob")
        data = response.json()
        # ID should be a string in JSON response
        assert isinstance(data["id"], str)


class TestFastAPIRoundtrip:
    def setup_method(self) -> None:
        users.clear()

    def test_create_and_fetch_preserves_id(self) -> None:
        # Create
        create_response = client.post("/users?name=Alice")
        created_id = create_response.json()["id"]

        # Fetch
        fetch_response = client.get(f"/users/{created_id}")
        fetched_id = fetch_response.json()["id"]

        # IDs should match exactly
        assert created_id == fetched_id
