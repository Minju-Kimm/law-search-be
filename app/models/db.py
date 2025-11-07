"""
SQLAlchemy Database Models
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


class User(Base):
    """User model for OAuth authentication"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    provider = Column(String, nullable=False)  # 'google' or 'naver'
    provider_id = Column(String, nullable=False)  # OAuth provider's user ID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")

    # Unique constraint for provider + provider_id
    __table_args__ = (
        UniqueConstraint('provider', 'provider_id', name='uq_provider_user'),
    )


class Bookmark(Base):
    """Bookmark model for saving law articles"""
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    law_code = Column(String, nullable=False)  # e.g., "CIVIL_CODE"
    article_no = Column(Integer, nullable=False)
    article_sub_no = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="bookmarks")

    # Unique constraint: one user can't bookmark the same article twice
    __table_args__ = (
        UniqueConstraint('user_id', 'law_code', 'article_no', 'article_sub_no', name='uq_user_bookmark'),
    )
