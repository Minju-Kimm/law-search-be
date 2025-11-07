"""
User profile routes
"""
from fastapi import APIRouter, Depends
from app.deps import get_current_user
from app.models import UserOut
from app.models.db import User

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user's profile

    Returns:
        UserOut: User profile information

    Requires:
        Valid JWT token in HttpOnly cookie
    """
    return current_user
