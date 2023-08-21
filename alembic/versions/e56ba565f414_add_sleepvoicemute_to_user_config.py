"""add sleepVoiceMute to user config

Revision ID: e56ba565f414
Revises: 3903394e1e7d
Create Date: 2023-08-21 15:31:37.230549

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e56ba565f414'
down_revision: Union[str, None] = '3903394e1e7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('userconfigs', sa.Column('voiceSleepMute', sa.Boolean(), nullable=False, server_default='false'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('userconfigs', 'voiceSleepMute')
    # ### end Alembic commands ###
