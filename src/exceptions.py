from typing import Any, Optional


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str = "Application error",
        status_code: int = 500,
        detail: Optional[Any] = None,
    ):
        # If detail is provided and message is generic default, align message with detail
        if detail is not None and message in (
            "Application error",
            "Validation error",
            "Resource not found",
            "Authentication failed",
            "Permission denied",
            "Database error",
            "Resource conflict",
            "Business logic error",
        ):
            message = str(detail)

        self.message = message
        self.status_code = status_code
        self.detail = detail if detail is not None else message
        super().__init__(self.message)


class ValidationError(AppException):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation error", detail: Optional[Any] = None):
        super().__init__(message, status_code=400, detail=detail)


class NotFoundError(AppException):
    """Raised when a resource is not found."""

    def __init__(self, message: str = "Resource not found", detail: Optional[Any] = None):
        super().__init__(message, status_code=404, detail=detail)


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", detail: Optional[Any] = None):
        super().__init__(message, status_code=401, detail=detail)


class AuthorizationError(AppException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Permission denied", detail: Optional[Any] = None):
        super().__init__(message, status_code=403, detail=detail)


class DatabaseError(AppException):
    """Raised when a database operation fails."""

    def __init__(self, message: str = "Database error", detail: Optional[Any] = None):
        super().__init__(message, status_code=500, detail=detail)


class ConflictError(AppException):
    """Raised when a resource conflict occurs (e.g., duplicate)."""

    def __init__(self, message: str = "Resource conflict", detail: Optional[Any] = None):
        super().__init__(message, status_code=409, detail=detail)


class BusinessLogicError(AppException):
    """Raised when a business logic rule is violated."""

    def __init__(
        self,
        message: str = "Business logic error",
        detail: Optional[Any] = None,
        status_code: int = 422,
    ):
        super().__init__(message, status_code=status_code, detail=detail)


# Backward-compatible alias
KnowraException = AppException
