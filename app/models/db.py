"""
SQLModel Database Models
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Index, UniqueConstraint
from sqlalchemy import Column, String, BigInteger, ForeignKey, text


class User(SQLModel, table=True):
    """User model for OAuth authentication"""
    __tablename__ = "users"

    id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    provider: str = Field(max_length=20, nullable=False)
    provider_id: str = Field(max_length=128, nullable=False)
    email: Optional[str] = Field(default=None, nullable=True, index=True)
    name: Optional[str] = Field(default=None, nullable=True)
    picture: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")}
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")}
    )

    __table_args__ = (
        UniqueConstraint('provider', 'provider_id', name='uq_provider_user'),
    )


class Bookmark(SQLModel, table=True):
    """Bookmark model for saving law articles"""
    __tablename__ = "bookmarks"

    id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    user_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    law_code: str = Field(max_length=64, nullable=False)
    article_no: str = Field(max_length=32, nullable=False)
    memo: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")}
    )

    __table_args__ = (
        UniqueConstraint('user_id', 'law_code', 'article_no', name='uq_user_bookmark'),
        Index('ix_bookmarks_law_article', 'law_code', 'article_no'),
    )
