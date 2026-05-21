"""legacy fotmob baseline (revision file restored for existing DBs)

Revision ID: 6f818e93c283
Revises:
Create Date: 2026-05-19

"""

from typing import Sequence, Union

revision: str = "6f818e93c283"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
