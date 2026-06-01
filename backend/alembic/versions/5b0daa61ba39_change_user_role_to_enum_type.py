"""change user_role to enum type

Revision ID: 5b0daa61ba39
Revises: 54e8b4b7c22d
Create Date: 2026-06-01 21:33:21.008674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b0daa61ba39'
down_revision: Union[str, Sequence[str], None] = '54e8b4b7c22d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


userrole_enum = sa.Enum('admin', 'reviewer', name='userrole')


def upgrade() -> None:
    """Upgrade schema."""
    userrole_enum.create(op.get_bind(), checkfirst=True)
    op.alter_column('user_info', 'user_role',
               existing_type=sa.VARCHAR(length=20),
               type_=userrole_enum,
               existing_nullable=False,
               postgresql_using='user_role::userrole')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('user_info', 'user_role',
               existing_type=userrole_enum,
               type_=sa.VARCHAR(length=20),
               existing_nullable=False,
               postgresql_using='user_role::text')
    userrole_enum.drop(op.get_bind(), checkfirst=True)
