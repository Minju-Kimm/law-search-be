"""
Database session management with SQLModel
"""
import os
from sqlmodel import create_engine, Session, SQLModel

DATABASE_URL = os.getenv("DATABASE_URL")

# Convert postgresql:// to postgresql+psycopg:// for psycopg3 driver
# SQLAlchemy 2.0 defaults to psycopg2, but we use psycopg3 (psycopg[binary])
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# SQLModel engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False  # Set to True for SQL query logging
)


def create_db_and_tables():
    """
    Create all tables in the database
    Note: For production, use Alembic migrations instead
    """
    SQLModel.metadata.create_all(engine)


def get_db():
    """
    Dependency for getting DB session

    Usage:
        @app.get("/")
        def route(db: Session = Depends(get_db)):
            ...
    """
    with Session(engine) as session:
        yield session
