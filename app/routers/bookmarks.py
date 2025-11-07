"""
Bookmarks CRUD routes
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db import get_db
from app.deps import get_current_user
from app.models import BookmarkCreate, BookmarkOut
from app.models.db import User, Bookmark

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])


@router.get("", response_model=List[BookmarkOut])
async def get_bookmarks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all bookmarks for the current user

    Returns:
        List of bookmarks ordered by creation date (newest first)

    Requires:
        Valid JWT token in HttpOnly cookie
    """
    bookmarks = db.query(Bookmark).filter(
        Bookmark.user_id == current_user.id
    ).order_by(Bookmark.created_at.desc()).all()

    # Convert to response model with camelCase
    return [
        BookmarkOut(
            id=b.id,
            lawCode=b.law_code,
            articleNo=b.article_no,
            articleSubNo=b.article_sub_no,
            created_at=b.created_at
        )
        for b in bookmarks
    ]


@router.post("", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    bookmark_data: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new bookmark

    Args:
        bookmark_data: Bookmark creation data (lawCode, articleNo, articleSubNo)

    Returns:
        Created bookmark

    Raises:
        409 Conflict: If bookmark already exists for this user

    Requires:
        Valid JWT token in HttpOnly cookie
    """
    # Create new bookmark
    new_bookmark = Bookmark(
        user_id=current_user.id,
        law_code=bookmark_data.lawCode,
        article_no=bookmark_data.articleNo,
        article_sub_no=bookmark_data.articleSubNo
    )

    try:
        db.add(new_bookmark)
        db.commit()
        db.refresh(new_bookmark)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bookmark already exists"
        )

    # Convert to response model
    return BookmarkOut(
        id=new_bookmark.id,
        lawCode=new_bookmark.law_code,
        articleNo=new_bookmark.article_no,
        articleSubNo=new_bookmark.article_sub_no,
        created_at=new_bookmark.created_at
    )


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a bookmark by ID

    Args:
        bookmark_id: Bookmark ID to delete

    Returns:
        204 No Content on success

    Raises:
        404 Not Found: If bookmark doesn't exist or doesn't belong to user

    Requires:
        Valid JWT token in HttpOnly cookie
    """
    # Find bookmark
    bookmark = db.query(Bookmark).filter(
        Bookmark.id == bookmark_id,
        Bookmark.user_id == current_user.id
    ).first()

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    # Delete bookmark
    db.delete(bookmark)
    db.commit()

    return None
