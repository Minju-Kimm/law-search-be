"""Models package"""
from app.models.api import *
from app.models.db import User, Bookmark

__all__ = [
    # API Models
    "SearchScope",
    "LawOut",
    "SearchHit",
    "SearchResponse",
    "ArticleOut",
    "HealthResponse",
    "UserOut",
    "BookmarkCreate",
    "BookmarkOut",
    # DB Models
    "User",
    "Bookmark",
]
