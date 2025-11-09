"""
Bookmarks CRUD routes
"""
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db import get_db
from app.deps import get_current_user
from app.models import BookmarkCreate, BookmarkOut
from app.models.db import User, Bookmark

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])


# Helper functions for input normalization
def normalize_law_code(data: BookmarkCreate) -> str:
    """
    Normalize law code from various input formats
    Priority: lawCode > lawType
    """
    if data.lawCode:
        return data.lawCode.upper()

    if data.lawType:
        law_type_map = {
            "civil": "CIVIL_CODE",
            "criminal": "CRIMINAL_CODE",
            "civil_procedure": "CIVIL_PROCEDURE_CODE",
            "criminal_procedure": "CRIMINAL_PROCEDURE_CODE"
        }
        normalized = law_type_map.get(data.lawType.lower())
        if normalized:
            return normalized

    raise ValueError("lawCode or lawType is required")


def normalize_article_no(data: BookmarkCreate) -> str:
    """
    Normalize article number from various input formats
    Priority: articleNo > joCode > heading
    """
    if data.articleNo:
        return str(data.articleNo).strip()

    if data.joCode:
        # joCode "076000" -> "760"
        try:
            article_no = str(int(data.joCode[:4]))  # First 4 digits
            return article_no
        except (ValueError, IndexError):
            pass

    if data.heading:
        # Extract number from "제760조" or "제760조의2"
        match = re.search(r'제(\d+)조', data.heading)
        if match:
            return match.group(1)

    raise ValueError("articleNo, joCode, or heading is required")


@router.get("", response_model=List[BookmarkOut])
async def get_bookmarks(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all bookmarks for the current user

    Args:
        limit: Maximum number of bookmarks to return (default: 100, max: 1000)
        offset: Number of bookmarks to skip for pagination (default: 0)

    Returns:
        List of bookmarks ordered by creation date (newest first)

    Requires:
        Valid JWT token in HttpOnly cookie
    """
    bookmarks = db.query(Bookmark).filter(
        Bookmark.user_id == current_user.id
    ).order_by(Bookmark.created_at.desc()).limit(limit).offset(offset).all()

    # Convert to response model with camelCase
    return [
        BookmarkOut(
            id=b.id,
            lawCode=b.law_code,
            articleNo=b.article_no,
            memo=b.memo,
            createdAt=b.created_at
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
        bookmark_data: Bookmark creation data (lawCode/lawType, articleNo/joCode/heading, memo)

    Returns:
        Created bookmark with camelCase fields

    Raises:
        400 Bad Request: If input validation fails
        409 Conflict: If bookmark already exists for this user

    Requires:
        Valid JWT token in HttpOnly cookie
    """
    # Normalize input data
    try:
        law_code = normalize_law_code(bookmark_data)
        article_no = normalize_article_no(bookmark_data)
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "VALIDATION_ERROR", "detail": str(e)}
        )

    # Create new bookmark
    new_bookmark = Bookmark(
        user_id=current_user.id,
        law_code=law_code,
        article_no=article_no,
        memo=bookmark_data.memo
    )

    try:
        db.add(new_bookmark)
        db.commit()
        db.refresh(new_bookmark)
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "DUPLICATE_BOOKMARK", "detail": "Bookmark already exists for this article"}
        )

    # Convert to response model
    return BookmarkOut(
        id=new_bookmark.id,
        lawCode=new_bookmark.law_code,
        articleNo=new_bookmark.article_no,
        memo=new_bookmark.memo,
        createdAt=new_bookmark.created_at
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
    # Find bookmark - must belong to current user
    bookmark = db.query(Bookmark).filter(
        Bookmark.id == bookmark_id,
        Bookmark.user_id == current_user.id
    ).first()

    if not bookmark:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "NOT_FOUND", "detail": "Bookmark not found or does not belong to user"}
        )

    # Delete bookmark
    db.delete(bookmark)
    db.commit()

    return None
