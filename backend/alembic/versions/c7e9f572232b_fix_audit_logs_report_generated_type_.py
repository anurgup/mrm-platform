"""fix audit_logs.report_generated type: bool to str

Revision ID: c7e9f572232b
Revises: b56c60c753bc
Create Date: 2026-07-16 22:05:42.325558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e9f572232b'
down_revision: Union[str, Sequence[str], None] = 'b56c60c753bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # batch_alter_table: plain ALTER COLUMN TYPE is not supported on sqlite
    # (it can only ADD/DROP/RENAME columns) — batch mode recreates the table
    # under the hood on sqlite, and is a plain ALTER on postgres.
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.alter_column('report_generated',
                   existing_type=sa.BOOLEAN(),
                   type_=sa.String(),
                   existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.alter_column('report_generated',
                   existing_type=sa.String(),
                   type_=sa.BOOLEAN(),
                   existing_nullable=True)
