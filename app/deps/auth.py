"""
Authentication dependencies for protected routes
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.db import User
from app.utils.jwt import verify_token


def get_token_from_cookie(request: Request) -> Optional[str]:
    """
    Extract JWT token from HttpOnly cookie

    Args:
        request: FastAPI request object

    Returns:
        JWT token string or None
    """
    return request.cookies.get("access_token")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token in cookie

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = get_token_from_cookie(request)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    # Verify token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Get user ID from token
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user
