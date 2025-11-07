# Database Migrations Guide

## Overview

This project uses SQLModel for ORM and Alembic for database migrations.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Database URL

Set the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
# Example:
export DATABASE_URL="postgresql://postgres:mypassword@localhost:5432/law"
```

Or add it to your `.env` file.

## Running Migrations

### Apply migrations (upgrade to latest)

```bash
alembic upgrade head
```

### Rollback migrations (downgrade one version)

```bash
alembic downgrade -1
```

### Check current migration version

```bash
alembic current
```

### View migration history

```bash
alembic history
```

## Creating New Migrations

### Auto-generate migration from model changes

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Create empty migration template

```bash
alembic revision -m "Description of changes"
```

## Database Models

### Users Table

- `id` (BIGSERIAL): Primary key
- `provider` (VARCHAR(20)): OAuth provider (e.g., 'google', 'naver')
- `provider_id` (VARCHAR(128)): Provider's user ID
- `email` (VARCHAR): User email (indexed)
- `name` (VARCHAR): User name (optional)
- `picture` (VARCHAR): Profile picture URL (optional)
- `created_at` (TIMESTAMP): Creation timestamp (default: now())
- `updated_at` (TIMESTAMP): Last update timestamp (default: now())

**Constraints:**
- UNIQUE(provider, provider_id)

### Bookmarks Table

- `id` (BIGSERIAL): Primary key
- `user_id` (BIGINT): Foreign key to users.id (ON DELETE CASCADE, indexed)
- `law_code` (VARCHAR(64)): Law code
- `article_no` (VARCHAR(32)): Article number
- `memo` (TEXT): Optional memo
- `created_at` (TIMESTAMP): Creation timestamp (default: now())

**Constraints:**
- UNIQUE(user_id, law_code, article_no)

**Indexes:**
- ix_bookmarks_user_id (user_id)
- ix_bookmarks_law_article (law_code, article_no)

## Repository Functions

The project includes repository functions for common database operations:

### User Repository (`app/repositories/user_repository.py`)

- `get_user_by_id(session, user_id)`: Get user by ID
- `get_user_by_provider(session, provider, provider_id)`: Get user by OAuth provider
- `create_user(session, provider, provider_id, email, name, picture)`: Create new user
- `update_user(session, user_id, email, name, picture)`: Update user information
- `delete_user(session, user_id)`: Delete user (cascades to bookmarks)

### Bookmark Repository (`app/repositories/bookmark_repository.py`)

- `get_bookmark_by_id(session, bookmark_id)`: Get bookmark by ID
- `get_bookmarks_by_user_id(session, user_id, limit, offset)`: Get all bookmarks for a user
- `get_bookmark_by_user_and_article(session, user_id, law_code, article_no)`: Get specific bookmark
- `create_bookmark(session, user_id, law_code, article_no, memo)`: Create new bookmark
- `update_bookmark_memo(session, bookmark_id, memo)`: Update bookmark memo
- `delete_bookmark(session, bookmark_id)`: Delete bookmark
- `delete_bookmarks_by_user_id(session, user_id)`: Delete all bookmarks for a user

## Usage Example

```python
from sqlmodel import Session
from app.db.session import engine
from app.repositories import create_user, create_bookmark

# Create a session
with Session(engine) as session:
    # Create a user
    user = create_user(
        session=session,
        provider="google",
        provider_id="123456789",
        email="user@example.com",
        name="John Doe",
        picture="https://example.com/photo.jpg"
    )

    # Create a bookmark
    bookmark = create_bookmark(
        session=session,
        user_id=user.id,
        law_code="CIVIL_CODE",
        article_no="1",
        memo="Important article"
    )
```

## Notes

- The migration system tracks which migrations have been applied to prevent duplicate runs
- Always backup your database before running migrations in production
- Test migrations in a development environment first
- SQLModel uses SQLAlchemy under the hood, providing both ORM and Pydantic validation
