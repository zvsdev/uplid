# tests/test_types.py
from __future__ import annotations


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
        from uplid import UPLIDType

        # Protocol should have @runtime_checkable decorator
        assert hasattr(UPLIDType, "__protocol_attrs__") or hasattr(
            UPLIDType, "_is_runtime_protocol"
        )


class TestUPLIDConformsToProtocol:
    def test_uplid_instance_matches_protocol(self) -> None:
        from uplid import UPLID, UPLIDType

        uid = UPLID.generate("usr")
        assert isinstance(uid, UPLIDType)

    def test_protocol_allows_generic_functions(self) -> None:
        from uplid import UPLID, UPLIDType

        def get_datetime(uplid: UPLIDType) -> float:
            return uplid.datetime.timestamp()

        uid = UPLID.generate("usr")
        ts = get_datetime(uid)
        assert ts > 0

    def test_protocol_allows_any_prefix(self) -> None:
        from uplid import UPLID, UPLIDType

        def format_id(uplid: UPLIDType) -> str:
            return f"[{uplid.prefix}] {uplid.datetime.isoformat()}"

        usr_id = UPLID.generate("usr")
        api_id = UPLID.generate("api_key")

        assert "[usr]" in format_id(usr_id)
        assert "[api_key]" in format_id(api_id)
