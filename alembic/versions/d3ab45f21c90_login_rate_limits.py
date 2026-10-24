"""store login rate limits in postgres

Revision ID: d3ab45f21c90
Revises: 81c13a0ee82a
"""

import sqlalchemy as sa

from alembic import op

revision = "d3ab45f21c90"
down_revision = "81c13a0ee82a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "login_rate_limits",
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("ip_hash", name=op.f("pk_login_rate_limits")),
    )


def downgrade():
    op.drop_table("login_rate_limits")
