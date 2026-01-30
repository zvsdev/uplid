from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from uplid import UPLID, UPLIDError, factory, parse


UserId = UPLID[Literal["usr"]]
OrgId = UPLID[Literal["org"]]
UserIdFactory = factory(UserId)
OrgIdFactory = factory(OrgId)
parse_user_id = parse(UserId)
parse_org_id = parse(OrgId)


# FastAPI validators - parameter names must match route parameters
def validate_user_id(user_id: str) -> UserId:
    try:
        return parse_user_id(user_id)
    except UPLIDError as e:
        raise HTTPException(422, f"Invalid user ID: {e}") from None


def validate_org_id(org_id: str) -> OrgId:
    try:
        return parse_org_id(org_id)
    except UPLIDError as e:
        raise HTTPException(422, f"Invalid org ID: {e}") from None


class User(BaseModel):
    id: UserId = Field(default_factory=UserIdFactory)
    name: str
    org_id: OrgId | None = None


app = FastAPI()
users: dict[str, User] = {}


@app.post("/users")
def create_user(name: str, org_id: str | None = None) -> User:
    parsed_org_id = validate_org_id(org_id) if org_id else None
    user = User(name=name, org_id=parsed_org_id)
    users[str(user.id)] = user
    return user


@app.get("/users/{user_id}")
def get_user(user_id: Annotated[UserId, Depends(validate_user_id)]) -> User:
    if str(user_id) not in users:
        raise HTTPException(404, "User not found")
    return users[str(user_id)]


@app.get("/users")
def list_users(org_id: Annotated[str | None, Query()] = None) -> list[User]:
    if org_id is None:
        return list(users.values())
    parsed_org_id = validate_org_id(org_id)
    return [u for u in users.values() if u.org_id == parsed_org_id]


@app.put("/users/{user_id}")
def update_user(
    user_id: Annotated[UserId, Depends(validate_user_id)],
    user: User,
) -> User:
    """Update user - validates UPLID in JSON body."""
    if str(user_id) != str(user.id):
        raise HTTPException(400, "User ID in path must match body")
    users[str(user.id)] = user
    return user


@app.post("/users/from-json")
def create_user_from_json(user: User) -> User:
    """Create user from JSON body - UPLID validated by Pydantic."""
    users[str(user.id)] = user
    return user


# Header validation - wraps validator with Header extraction
def validate_user_id_header(x_user_id: Annotated[str, Header()]) -> UserId:
    return validate_user_id(x_user_id)


@app.get("/me")
def get_current_user(
    user_id: Annotated[UserId, Depends(validate_user_id_header)],
) -> User:
    """Get user from X-User-Id header."""
    if str(user_id) not in users:
        raise HTTPException(404, "User not found")
    return users[str(user_id)]


# Cookie validation - wraps validator with Cookie extraction
def validate_user_id_cookie(session_user_id: Annotated[str, Cookie()]) -> UserId:
    return validate_user_id(session_user_id)


@app.get("/session")
def get_session(
    user_id: Annotated[UserId, Depends(validate_user_id_cookie)],
) -> User:
    """Get user from session_user_id cookie."""
    if str(user_id) not in users:
        raise HTTPException(404, "User not found")
    return users[str(user_id)]


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
        org_id = OrgIdFactory()
        response = client.get(f"/users/{org_id}")
        assert response.status_code == 422

    def test_user_not_found_returns_404(self) -> None:
        valid_but_nonexistent = UserIdFactory()
        response = client.get(f"/users/{valid_but_nonexistent}")
        assert response.status_code == 404


class TestFastAPIQueryParams:
    def setup_method(self) -> None:
        users.clear()

    def test_filter_by_org_id(self) -> None:
        org1 = OrgIdFactory()
        org2 = OrgIdFactory()

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


class TestFastAPIJsonBody:
    """Test UPLID validation in JSON request bodies."""

    def setup_method(self) -> None:
        users.clear()

    def test_valid_uplid_in_json_body(self) -> None:
        """FastAPI validates UPLID in JSON body via Pydantic."""
        user_id = UserIdFactory()
        org_id = OrgIdFactory()

        response = client.post(
            "/users/from-json",
            json={"id": str(user_id), "name": "Alice", "org_id": str(org_id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user_id)
        assert data["name"] == "Alice"
        assert data["org_id"] == str(org_id)

    def test_invalid_uplid_format_in_body_returns_422(self) -> None:
        """Invalid UPLID format in body is rejected."""
        response = client.post(
            "/users/from-json",
            json={"id": "not_valid", "name": "Bob"},
        )

        assert response.status_code == 422
        # Pydantic validation error should indicate the problem
        assert "id" in response.text  # Error is on the id field

    def test_wrong_prefix_in_body_returns_422(self) -> None:
        """Wrong prefix (org instead of usr) in body is rejected."""
        org_id = OrgIdFactory()  # Wrong prefix for UserId field

        response = client.post(
            "/users/from-json",
            json={"id": str(org_id), "name": "Charlie"},
        )

        assert response.status_code == 422

    def test_wrong_org_prefix_in_body_returns_422(self) -> None:
        """Wrong prefix for org_id field is rejected."""
        user_id = UserIdFactory()
        another_user_id = UserIdFactory()  # Wrong prefix for OrgId field

        response = client.post(
            "/users/from-json",
            json={"id": str(user_id), "name": "Dave", "org_id": str(another_user_id)},
        )

        assert response.status_code == 422

    def test_update_with_matching_ids(self) -> None:
        """PUT with matching path and body IDs succeeds."""
        user_id = UserIdFactory()

        response = client.put(
            f"/users/{user_id}",
            json={"id": str(user_id), "name": "Updated"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_update_with_mismatched_ids_returns_400(self) -> None:
        """PUT with different path and body IDs fails."""
        user_id1 = UserIdFactory()
        user_id2 = UserIdFactory()

        response = client.put(
            f"/users/{user_id1}",
            json={"id": str(user_id2), "name": "Mismatch"},
        )

        assert response.status_code == 400


class TestPydanticSerialization:
    """Test Pydantic model serialization to/from JSON."""

    def test_model_dump_json_and_validate_json_roundtrip(self) -> None:
        """User model roundtrips through JSON."""
        original = User(name="Alice", org_id=OrgIdFactory())

        # Serialize to JSON string
        json_str = original.model_dump_json()

        # Deserialize back
        restored = User.model_validate_json(json_str)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.org_id == original.org_id

    def test_model_dump_returns_string_ids(self) -> None:
        """model_dump() returns string IDs, not UPLID objects."""
        user = User(name="Bob")
        data = user.model_dump()

        assert isinstance(data["id"], str)
        assert data["id"].startswith("usr_")

    def test_model_validate_from_dict_with_string_ids(self) -> None:
        """model_validate() accepts string IDs."""
        user_id = UserIdFactory()
        org_id = OrgIdFactory()

        user = User.model_validate(
            {
                "id": str(user_id),
                "name": "Charlie",
                "org_id": str(org_id),
            }
        )

        assert user.id == user_id
        assert user.org_id == org_id

    def test_model_validate_from_dict_with_uplid_objects(self) -> None:
        """model_validate() also accepts UPLID objects directly."""
        user_id = UserIdFactory()
        org_id = OrgIdFactory()

        user = User.model_validate(
            {
                "id": user_id,
                "name": "Diana",
                "org_id": org_id,
            }
        )

        assert user.id == user_id
        assert user.org_id == org_id

    def test_json_roundtrip_preserves_timestamps(self) -> None:
        """Timestamps are preserved through JSON roundtrip."""
        original = User(name="Eve")
        original_datetime = original.id.datetime

        json_str = original.model_dump_json()
        restored = User.model_validate_json(json_str)

        assert restored.id.datetime == original_datetime
        assert restored.id.timestamp == original.id.timestamp


class TestFastAPIHeaders:
    """Test UPLID validation in HTTP headers."""

    def setup_method(self) -> None:
        users.clear()

    def test_valid_user_id_in_header(self) -> None:
        """Valid UPLID in X-User-Id header is accepted."""
        # Create a user first
        response = client.post("/users?name=Alice")
        user_id = response.json()["id"]

        # Fetch via header
        response = client.get("/me", headers={"X-User-Id": user_id})
        assert response.status_code == 200
        assert response.json()["name"] == "Alice"

    def test_invalid_user_id_in_header_returns_422(self) -> None:
        """Invalid UPLID format in header is rejected."""
        response = client.get("/me", headers={"X-User-Id": "not_valid"})
        assert response.status_code == 422

    def test_wrong_prefix_in_header_returns_422(self) -> None:
        """Wrong prefix in header is rejected."""
        org_id = OrgIdFactory()
        response = client.get("/me", headers={"X-User-Id": str(org_id)})
        assert response.status_code == 422

    def test_missing_header_returns_422(self) -> None:
        """Missing required header returns 422."""
        response = client.get("/me")
        assert response.status_code == 422

    def test_user_not_found_via_header_returns_404(self) -> None:
        """Valid UPLID but non-existent user returns 404."""
        valid_but_nonexistent = UserIdFactory()
        response = client.get("/me", headers={"X-User-Id": str(valid_but_nonexistent)})
        assert response.status_code == 404


class TestFastAPICookies:
    """Test UPLID validation in cookies."""

    def setup_method(self) -> None:
        users.clear()

    def test_valid_user_id_in_cookie(self) -> None:
        """Valid UPLID in session cookie is accepted."""
        # Create a user first
        response = client.post("/users?name=Bob")
        user_id = response.json()["id"]

        # Fetch via cookie
        response = client.get("/session", cookies={"session_user_id": user_id})
        assert response.status_code == 200
        assert response.json()["name"] == "Bob"

    def test_invalid_user_id_in_cookie_returns_422(self) -> None:
        """Invalid UPLID format in cookie is rejected."""
        response = client.get("/session", cookies={"session_user_id": "bad_cookie"})
        assert response.status_code == 422

    def test_wrong_prefix_in_cookie_returns_422(self) -> None:
        """Wrong prefix in cookie is rejected."""
        org_id = OrgIdFactory()
        response = client.get("/session", cookies={"session_user_id": str(org_id)})
        assert response.status_code == 422

    def test_missing_cookie_returns_422(self) -> None:
        """Missing required cookie returns 422."""
        response = client.get("/session")
        assert response.status_code == 422

    def test_user_not_found_via_cookie_returns_404(self) -> None:
        """Valid UPLID but non-existent user returns 404."""
        valid_but_nonexistent = UserIdFactory()
        response = client.get("/session", cookies={"session_user_id": str(valid_but_nonexistent)})
        assert response.status_code == 404
