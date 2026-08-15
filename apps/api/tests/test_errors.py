from app.errors import error_envelope


def test_error_envelope_shape() -> None:
    envelope = error_envelope("SOME_CODE", "some message", {"field": "x"})
    assert envelope == {
        "error": {"code": "SOME_CODE", "message": "some message", "details": {"field": "x"}}
    }


def test_error_envelope_defaults_details_to_none() -> None:
    envelope = error_envelope("SOME_CODE", "some message")
    assert envelope["error"]["details"] is None
