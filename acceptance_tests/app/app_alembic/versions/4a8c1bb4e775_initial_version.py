"""Initial version

Revision ID: 4a8c1bb4e775
Revises:
Create Date: 2016-09-14 09:23:27.466418

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '4a8c1bb4e775'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("""
    CREATE TABLE hello (
      id SERIAL PRIMARY KEY,
      value TEXT UNIQUE INITIALLY DEFERRED
    )
    """)


def downgrade():
    pass
