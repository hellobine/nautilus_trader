from quantdeck_backend.models.common import ApiError


def test_api_error_shape():
    err = ApiError(code="not_found", message="缺失")
    dumped = err.model_dump()
    assert dumped == {"code": "not_found", "message": "缺失", "detail": None}
