"""
Shared dependencies for FastAPI routes.

This module provides dependency injection for:
- Database sessions
- Authentication
- Request context
"""

from typing import Generator, Optional
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Request, Header, HTTPException


# ============================================================================
# Request Context
# ============================================================================


class RequestContext:
    """
    Request context for tracking and logging.

    Provides request ID and timestamp for correlation.
    """

    def __init__(self, request_id: str, timestamp: datetime):
        self.request_id = request_id
        self.timestamp = timestamp


def get_request_context(
    request: Request,
    x_request_id: Optional[str] = Header(None),
) -> RequestContext:
    """
    Get request context for tracking.

    Args:
        request: FastAPI request object
        x_request_id: Optional request ID from header

    Returns:
        RequestContext with ID and timestamp
    """
    request_id = x_request_id or str(uuid4())
    return RequestContext(
        request_id=request_id,
        timestamp=datetime.now(timezone.utc),
    )


# ============================================================================
# Database Session (Stub)
# ============================================================================


class DatabaseSession:
    """
    Database session stub.

    TODO: Replace with actual SQLAlchemy async session when database is set up.
    """

    def __init__(self):
        self._connected = False

    async def connect(self):
        """Connect to database."""
        self._connected = True

    async def disconnect(self):
        """Disconnect from database."""
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected


async def get_db() -> Generator[DatabaseSession, None, None]:
    """
    Get database session dependency.

    Usage:
        @router.get("/items")
        async def get_items(db: DatabaseSession = Depends(get_db)):
            ...

    Yields:
        Database session
    """
    db = DatabaseSession()
    try:
        await db.connect()
        yield db
    finally:
        await db.disconnect()


# ============================================================================
# Authentication (Stub)
# ============================================================================


class CurrentUser:
    """
    Current authenticated user.

    TODO: Implement actual JWT validation when auth is set up.
    """

    def __init__(self, user_id: str, email: str, roles: list[str]):
        self.user_id = user_id
        self.email = email
        self.roles = roles

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles


async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> CurrentUser:
    """
    Get current authenticated user.

    TODO: Implement actual JWT validation.

    Args:
        authorization: Bearer token from header

    Returns:
        CurrentUser object

    Raises:
        HTTPException: 401 if not authenticated
    """
    # TODO: Implement actual auth
    # For now, return a mock user for development

    # Uncomment to require auth:
    # if not authorization or not authorization.startswith("Bearer "):
    #     raise HTTPException(status_code=401, detail="Not authenticated")

    return CurrentUser(
        user_id="user-001",
        email="dev@example.com",
        roles=["user", "admin"],
    )


async def require_admin(
    current_user: CurrentUser,
) -> CurrentUser:
    """
    Require admin role.

    Args:
        current_user: Current authenticated user

    Returns:
        CurrentUser if admin

    Raises:
        HTTPException: 403 if not admin
    """
    if not current_user.has_role("admin"):
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user
