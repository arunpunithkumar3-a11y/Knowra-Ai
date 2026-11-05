from src.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    ConflictError,
    DatabaseError,
    NotFoundError,
    ValidationError,
)


def test_app_exception_defaults():
    exc = AppException()
    assert exc.message == "Application error"
    assert exc.status_code == 500
    assert exc.detail == "Application error"


def test_app_exception_custom_message():
    exc = AppException(message="Custom server error", status_code=502, detail="Gateway error")
    assert exc.message == "Custom server error"
    assert exc.status_code == 502
    assert exc.detail == "Gateway error"


def test_validation_error():
    exc = ValidationError(detail="Invalid field format")
    assert exc.status_code == 400
    assert exc.detail == "Invalid field format"
    assert exc.message == "Invalid field format"


def test_not_found_error():
    exc = NotFoundError(detail="Item not found")
    assert exc.status_code == 404
    assert exc.detail == "Item not found"


def test_authentication_error():
    exc = AuthenticationError(detail="Bad credentials")
    assert exc.status_code == 401
    assert exc.detail == "Bad credentials"


def test_authorization_error():
    exc = AuthorizationError(detail="Forbidden action")
    assert exc.status_code == 403
    assert exc.detail == "Forbidden action"


def test_conflict_error():
    exc = ConflictError(detail="Already exists")
    assert exc.status_code == 409
    assert exc.detail == "Already exists"


def test_database_error():
    exc = DatabaseError(detail="DB down")
    assert exc.status_code == 500
    assert exc.detail == "DB down"


def test_business_logic_error():
    exc = BusinessLogicError(detail="Operation not permitted")
    assert exc.status_code == 422
    assert exc.detail == "Operation not permitted"
