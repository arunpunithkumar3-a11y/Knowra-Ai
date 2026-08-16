from typing import Any, Optional


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        detail: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


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
    
    def __init__(self, message: str = "Not authorized", detail: Optional[Any] = None):
        super().__init__(message, status_code=403, detail=detail)


class DatabaseError(AppException):
    """Raised when a database operation fails."""
    
    def __init__(self, message: str = "Database error", detail: Optional[Any] = None):
        super().__init__(message, status_code=500, detail=detail)


class ConflictError(AppException):
    """Raised when a resource conflict occurs (e.g., duplicate)."""
    
    def __init__(self, message: str = "Resource conflict", detail: Optional[Any] = None):
        super().__init__(message, status_code=409, detail=detail)