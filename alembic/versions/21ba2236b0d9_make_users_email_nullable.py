"""Make users.email nullable

Revision ID: 21ba2236b0d9
Revises: 37f6c74fdc76
Create Date: 2025-11-07 10:00:55.924565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21ba2236b0d9'
down_revision: Union[str, None] = '37f6c74fdc76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make email column nullable
    op.alter_column('users', 'email',
                    existing_type=sa.String(),
                    nullable=True)


def downgrade() -> None:
    # Make email column not nullable (may fail if there are NULL values)
    op.alter_column('users', 'email',
                    existing_type=sa.String(),
                    nullable=False)
