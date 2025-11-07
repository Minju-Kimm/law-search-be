"""
User repository for database operations
"""
from typing import Optional
from sqlmodel import Session, select
from app.models.db import User


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """
    Get user by ID

    Args:
        session: Database session
        user_id: User ID

    Returns:
        User object or None if not found
    """
    return session.get(User, user_id)


def get_user_by_provider(
    session: Session,
    provider: str,
    provider_id: str
) -> Optional[User]:
    """
    Get user by OAuth provider and provider ID

    Args:
        session: Database session
        provider: OAuth provider (e.g., 'google', 'naver')
        provider_id: Provider's user ID

    Returns:
        User object or None if not found
    """
    statement = select(User).where(
        User.provider == provider,
        User.provider_id == provider_id
    )
    return session.exec(statement).first()


def create_user(
    session: Session,
    provider: str,
    provider_id: str,
    email: str,
    name: Optional[str] = None,
    picture: Optional[str] = None
) -> User:
    """
    Create a new user

    Args:
        session: Database session
        provider: OAuth provider
        provider_id: Provider's user ID
        email: User email
        name: User name (optional)
        picture: Profile picture URL (optional)

    Returns:
        Created User object
    """
    user = User(
        provider=provider,
        provider_id=provider_id,
        email=email,
        name=name,
        picture=picture
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user(
    session: Session,
    user_id: int,
    email: Optional[str] = None,
    name: Optional[str] = None,
    picture: Optional[str] = None
) -> Optional[User]:
    """
    Update user information

    Args:
        session: Database session
        user_id: User ID
        email: New email (optional)
        name: New name (optional)
        picture: New picture URL (optional)

    Returns:
        Updated User object or None if not found
    """
    user = session.get(User, user_id)
    if not user:
        return None

    if email is not None:
        user.email = email
    if name is not None:
        user.name = name
    if picture is not None:
        user.picture = picture

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def delete_user(session: Session, user_id: int) -> bool:
    """
    Delete a user (will cascade delete all bookmarks)

    Args:
        session: Database session
        user_id: User ID

    Returns:
        True if deleted, False if not found
    """
    user = session.get(User, user_id)
    if not user:
        return False

    session.delete(user)
    session.commit()
    return True
