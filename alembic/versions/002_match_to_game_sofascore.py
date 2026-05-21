"""rename match_* tables to game_* for Sofascore code

Revision ID: 002_match_to_game
Revises: 6f818e93c283
Create Date: 2026-05-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_match_to_game"
down_revision: Union[str, None] = "6f818e93c283"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "match_logs" not in inspector.get_table_names():
        return

    op.add_column("match_infos", sa.Column("home_team_name", sa.String(length=255), nullable=True))
    op.add_column("match_infos", sa.Column("away_team_name", sa.String(length=255), nullable=True))
    op.add_column("match_infos", sa.Column("league", sa.String(length=128), nullable=True))
    op.add_column("match_infos", sa.Column("season", sa.String(length=32), nullable=True))

    op.execute(
        """
        UPDATE match_infos AS mi
        SET home_team_name = ht.name,
            away_team_name = at.name
        FROM teams AS ht, teams AS at
        WHERE mi.home_team_id = ht.id
          AND mi.away_team_id = at.id
        """
    )

    op.alter_column("match_infos", "home_team_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("match_infos", "away_team_id", existing_type=sa.Integer(), nullable=True)

    op.rename_table("match_logs", "games")
    op.execute("ALTER TABLE games ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS match_logs_id_seq")

    op.rename_table("match_infos", "game_infos")
    op.rename_table("match_details", "game_details")

    op.drop_constraint("fk_player_match_details_match_details", "player_match_details", type_="foreignkey")
    op.drop_constraint("player_match_details_match_id_fkey", "player_match_details", type_="foreignkey")
    op.alter_column("player_match_details", "match_id", new_column_name="game_id")
    op.rename_table("player_match_details", "player_game_details")

    op.create_foreign_key(
        "player_game_details_game_id_fkey",
        "player_game_details",
        "games",
        ["game_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_player_game_details_game_details",
        "player_game_details",
        "game_details",
        ["game_id", "team_id"],
        ["id", "team_id"],
    )

    op.execute("ALTER TABLE teams ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS teams_id_seq")
    op.execute("ALTER TABLE players ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS players_id_seq")


def downgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS players_id_seq OWNED BY players.id")
    op.execute("ALTER TABLE players ALTER COLUMN id SET DEFAULT nextval('players_id_seq')")
    op.execute("CREATE SEQUENCE IF NOT EXISTS teams_id_seq OWNED BY teams.id")
    op.execute("ALTER TABLE teams ALTER COLUMN id SET DEFAULT nextval('teams_id_seq')")

    op.drop_constraint("fk_player_game_details_game_details", "player_game_details", type_="foreignkey")
    op.drop_constraint("player_game_details_game_id_fkey", "player_game_details", type_="foreignkey")
    op.rename_table("player_game_details", "player_match_details")
    op.alter_column("player_match_details", "game_id", new_column_name="match_id")
    op.create_foreign_key(
        "player_match_details_match_id_fkey",
        "player_match_details",
        "games",
        ["match_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_player_match_details_match_details",
        "player_match_details",
        "game_details",
        ["match_id", "team_id"],
        ["id", "team_id"],
    )

    op.rename_table("game_details", "match_details")
    op.rename_table("game_infos", "match_infos")
    op.execute("CREATE SEQUENCE IF NOT EXISTS match_logs_id_seq OWNED BY games.id")
    op.execute("ALTER TABLE games ALTER COLUMN id SET DEFAULT nextval('match_logs_id_seq')")
    op.rename_table("games", "match_logs")

    op.execute(
        """
        DELETE FROM match_infos
        WHERE home_team_id IS NULL OR away_team_id IS NULL
        """
    )
    op.execute(
        """
        DELETE FROM match_logs ml
        WHERE NOT EXISTS (
            SELECT 1 FROM match_infos mi WHERE mi.id = ml.id
        )
        """
    )

    op.alter_column("match_infos", "away_team_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("match_infos", "home_team_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("match_infos", "season")
    op.drop_column("match_infos", "league")
    op.drop_column("match_infos", "away_team_name")
    op.drop_column("match_infos", "home_team_name")
