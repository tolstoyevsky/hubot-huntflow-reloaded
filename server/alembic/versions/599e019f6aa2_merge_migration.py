"""merge_migration

Revision ID: 599e019f6aa2
Revises: 38bdbf24dd4a, 68b26cae15dc
Create Date: 2019-05-30 15:08:18.355296

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '599e019f6aa2'
down_revision = ('38bdbf24dd4a', '68b26cae15dc')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
