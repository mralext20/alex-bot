"""add auto reaction to reminders

Revision ID: c4f9a55af340
Revises: 5bee6f5c272e
Create Date: 2024-06-25 17:19:59.919372

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f9a55af340'
down_revision: Union[str, None] = '5bee6f5c272e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        'reminders',
        sa.Column(
            'auto_react',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('reminders', 'auto_react')
    # ### end Alembic commands ###
