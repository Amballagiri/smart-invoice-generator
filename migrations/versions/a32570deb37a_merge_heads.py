"""merge heads

Revision ID: a32570deb37a
Revises: a1b2c3d4e5f6, 3f2b1c0a9d8e
Create Date: 2026-08-10 14:56:53.452452

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a32570deb37a'
down_revision = ('a1b2c3d4e5f6', '3f2b1c0a9d8e')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
