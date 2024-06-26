"""Add Mudae series Map

Revision ID: 5bee6f5c272e
Revises: ca032db10a65
Create Date: 2024-06-17 19:43:08.163862

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bee6f5c272e'
down_revision: Union[str, None] = 'ca032db10a65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'mudaeSeriesRequests',
        sa.Column('series', sa.String(), nullable=False),
        sa.Column('requestedBy', sa.BIGINT(), nullable=False),
        sa.PrimaryKeyConstraint('series', 'requestedBy'),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('mudaeSeriesRequests')
    # ### end Alembic commands ###
