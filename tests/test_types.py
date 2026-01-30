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
