"""
Repository layer for database operations
"""
from .user_repository import (
    get_user_by_id,
    get_user_by_provider,
    create_user,
    update_user,
    delete_user,
)
from .bookmark_repository import (
    get_bookmark_by_id,
    get_bookmarks_by_user_id,
    get_bookmark_by_user_and_article,
    create_bookmark,
    delete_bookmark,
    delete_bookmarks_by_user_id,
)

__all__ = [
    # User repository
    "get_user_by_id",
    "get_user_by_provider",
    "create_user",
    "update_user",
    "delete_user",
    # Bookmark repository
    "get_bookmark_by_id",
    "get_bookmarks_by_user_id",
    "get_bookmark_by_user_and_article",
    "create_bookmark",
    "delete_bookmark",
    "delete_bookmarks_by_user_id",
]
