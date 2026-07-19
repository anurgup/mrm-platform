"""fix findings.regulatory_reference type: str to JSON dict

Revision ID: cf078ba87f00
Revises: 152864ab753e
Create Date: 2026-07-19 19:31:43.192247

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf078ba87f00'
down_revision: Union[str, Sequence[str], None] = '152864ab753e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # batch_alter_table: plain ALTER COLUMN TYPE is not supported on sqlite —
    # batch mode recreates the table under the hood there, plain ALTER on postgres.
    with op.batch_alter_table('findings') as batch_op:
        batch_op.alter_column('regulatory_reference',
                   existing_type=sa.VARCHAR(),
                   type_=sa.JSON(),
                   existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('findings') as batch_op:
        batch_op.alter_column('regulatory_reference',
                   existing_type=sa.JSON(),
                   type_=sa.VARCHAR(),
                   existing_nullable=True)
