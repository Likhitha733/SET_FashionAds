"""Centralized error handling for the Fashion Ad Generator"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class AppException(Exception):
    """Base exception for application errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class AuthenticationError(AppException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 401)

class AuthorizationError(AppException):
    """Raised when user lacks permissions"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, 403)

class NotFoundError(AppException):
    """Raised when resource not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)

class ValidationError(AppException):
    """Raised when validation fails"""
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, 400)

class QuotaExceededError(AppException):
    """Raised when usage quota exceeded"""
    def __init__(self, message: str = "Usage quota exceeded"):
        super().__init__(message, 429)

async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions"""
    logger.error(f"AppException: {exc.message} (Status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
