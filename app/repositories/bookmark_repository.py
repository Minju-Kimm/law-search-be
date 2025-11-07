"""
Bookmark repository for database operations
"""
from typing import Optional, List
from sqlmodel import Session, select
from app.models.db import Bookmark


def get_bookmark_by_id(session: Session, bookmark_id: int) -> Optional[Bookmark]:
    """
    Get bookmark by ID

    Args:
        session: Database session
        bookmark_id: Bookmark ID

    Returns:
        Bookmark object or None if not found
    """
    return session.get(Bookmark, bookmark_id)


def get_bookmarks_by_user_id(
    session: Session,
    user_id: int,
    limit: int = 100,
    offset: int = 0
) -> List[Bookmark]:
    """
    Get all bookmarks for a user

    Args:
        session: Database session
        user_id: User ID
        limit: Maximum number of bookmarks to return (default: 100)
        offset: Number of bookmarks to skip (default: 0)

    Returns:
        List of Bookmark objects
    """
    statement = (
        select(Bookmark)
        .where(Bookmark.user_id == user_id)
        .order_by(Bookmark.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.exec(statement).all())


def get_bookmark_by_user_and_article(
    session: Session,
    user_id: int,
    law_code: str,
    article_no: str
) -> Optional[Bookmark]:
    """
    Get a specific bookmark by user and article

    Args:
        session: Database session
        user_id: User ID
        law_code: Law code
        article_no: Article number

    Returns:
        Bookmark object or None if not found
    """
    statement = select(Bookmark).where(
        Bookmark.user_id == user_id,
        Bookmark.law_code == law_code,
        Bookmark.article_no == article_no
    )
    return session.exec(statement).first()


def create_bookmark(
    session: Session,
    user_id: int,
    law_code: str,
    article_no: str,
    memo: Optional[str] = None
) -> Bookmark:
    """
    Create a new bookmark

    Args:
        session: Database session
        user_id: User ID
        law_code: Law code (max 64 chars)
        article_no: Article number (max 32 chars)
        memo: Optional memo

    Returns:
        Created Bookmark object
    """
    bookmark = Bookmark(
        user_id=user_id,
        law_code=law_code,
        article_no=article_no,
        memo=memo
    )
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)
    return bookmark


def update_bookmark_memo(
    session: Session,
    bookmark_id: int,
    memo: Optional[str]
) -> Optional[Bookmark]:
    """
    Update bookmark memo

    Args:
        session: Database session
        bookmark_id: Bookmark ID
        memo: New memo text

    Returns:
        Updated Bookmark object or None if not found
    """
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        return None

    bookmark.memo = memo
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)
    return bookmark


def delete_bookmark(session: Session, bookmark_id: int) -> bool:
    """
    Delete a bookmark

    Args:
        session: Database session
        bookmark_id: Bookmark ID

    Returns:
        True if deleted, False if not found
    """
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        return False

    session.delete(bookmark)
    session.commit()
    return True


def delete_bookmarks_by_user_id(session: Session, user_id: int) -> int:
    """
    Delete all bookmarks for a user

    Args:
        session: Database session
        user_id: User ID

    Returns:
        Number of bookmarks deleted
    """
    statement = select(Bookmark).where(Bookmark.user_id == user_id)
    bookmarks = session.exec(statement).all()
    count = len(bookmarks)

    for bookmark in bookmarks:
        session.delete(bookmark)

    session.commit()
    return count
