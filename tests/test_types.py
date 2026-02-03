from __future__ import annotations

from uplid import UPLIDError, UPLIDType

from .conftest import ApiKeyIdFactory, UserIdFactory


class TestUPLIDError:
    def test_is_value_error_subclass(self) -> None:
        assert issubclass(UPLIDError, ValueError)

    def test_can_catch_as_value_error(self) -> None:
        try:
            raise UPLIDError("test message")
        except ValueError as e:
            assert str(e) == "test message"


class TestUPLIDTypeProtocol:
    def test_protocol_has_required_attributes(self) -> None:
        assert hasattr(UPLIDType, "prefix")
        assert hasattr(UPLIDType, "uid")
        assert hasattr(UPLIDType, "datetime")

    def test_protocol_is_runtime_checkable(self) -> None:
        # Protocol should have @runtime_checkable decorator
        assert hasattr(UPLIDType, "__protocol_attrs__") or hasattr(
            UPLIDType, "_is_runtime_protocol"
        )


class TestUPLIDConformsToProtocol:
    def test_uplid_instance_matches_protocol(self) -> None:
        uid = UserIdFactory()
        assert isinstance(uid, UPLIDType)

    def test_protocol_allows_generic_functions(self) -> None:
        def get_datetime(uplid: UPLIDType) -> float:
            return uplid.datetime.timestamp()

        uid = UserIdFactory()
        ts = get_datetime(uid)
        assert ts > 0

    def test_protocol_allows_any_prefix(self) -> None:
        def format_id(uplid: UPLIDType) -> str:
            return f"[{uplid.prefix}] {uplid.datetime.isoformat()}"

        usr_id = UserIdFactory()
        api_id = ApiKeyIdFactory()

        assert "[usr]" in format_id(usr_id)
        assert "[api_key]" in format_id(api_id)
