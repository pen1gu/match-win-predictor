"""init sofascore schema

Revision ID: 001_init
Revises: 002_match_to_game
Create Date: 2026-05-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_init"
down_revision: Union[str, None] = "002_match_to_game"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "games" in inspector.get_table_names():
        return

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=128), nullable=True),
        sa.Column("league", sa.String(length=128), nullable=True),
        sa.Column("league_id", sa.Integer(), nullable=True),
        sa.Column("founded", sa.Integer(), nullable=True),
        sa.Column("stadium", sa.String(length=255), nullable=True),
        sa.Column("stadium_capacity", sa.Integer(), nullable=True),
        sa.Column("stadium_location", sa.String(length=255), nullable=True),
        sa.Column("stadium_city", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "player_infos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("position", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("role", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("shirt_number", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=True),
        sa.Column("birth_date", sa.String(length=32), nullable=True),
        sa.Column("birth_place", sa.String(length=255), nullable=True),
        sa.Column("birth_country", sa.String(length=128), nullable=True),
        sa.Column("birth_state", sa.String(length=128), nullable=True),
        sa.Column("nationality_code", sa.String(length=16), nullable=True),
        sa.Column("current_market_value", sa.Integer(), nullable=True),
        sa.Column("fan_rating", sa.Float(), nullable=True),
        sa.Column("season_statistics", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "player_match_affect_features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("performance_trend", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("injury_history", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("current_form", sa.String(length=32), nullable=True),
        sa.Column("form_rating", sa.Float(), nullable=True),
        sa.Column("recent_matches", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("availability_status", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "player_ratings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_ratings_player_id", "player_ratings", ["player_id"])
    op.create_table(
        "game_infos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=True),
        sa.Column("away_team_id", sa.Integer(), nullable=True),
        sa.Column("home_team_name", sa.String(length=255), nullable=True),
        sa.Column("away_team_name", sa.String(length=255), nullable=True),
        sa.Column("match_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("match_name", sa.String(), nullable=True),
        sa.Column("league_name", sa.String(), nullable=True),
        sa.Column("league", sa.String(length=128), nullable=True),
        sa.Column("season", sa.String(length=32), nullable=True),
        sa.Column("match_round", sa.String(), nullable=True),
        sa.Column("match_time_utc", sa.String(), nullable=True),
        sa.Column("stadium", sa.String(), nullable=True),
        sa.Column("referee", sa.String(), nullable=True),
        sa.Column("attendance", sa.Integer(), nullable=True),
        sa.Column("weather", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("next_match", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("finished", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cancelled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("halfs_info", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("events", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("shotmap", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "game_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("is_home", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("penalty_score", sa.Integer(), nullable=True),
        sa.Column("is_penalty_loser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("score_str", sa.String(), nullable=True),
        sa.Column("penalty_shootout_reason", sa.String(), nullable=True),
        sa.Column("expected_goals_value", sa.Float(), nullable=True),
        sa.Column("expected_assists_value", sa.Float(), nullable=True),
        sa.Column("expected_goals_on_target_value", sa.Float(), nullable=True),
        sa.Column("possession", sa.Float(), nullable=True),
        sa.Column("shots_total", sa.Integer(), nullable=True),
        sa.Column("shots_on_target", sa.Integer(), nullable=True),
        sa.Column("big_chances", sa.Integer(), nullable=True),
        sa.Column("big_chances_missed", sa.Integer(), nullable=True),
        sa.Column("corners", sa.Integer(), nullable=True),
        sa.Column("fouls", sa.Integer(), nullable=True),
        sa.Column("yellow_cards", sa.Integer(), nullable=True),
        sa.Column("red_cards", sa.Integer(), nullable=True),
        sa.Column("accurate_passes", sa.Integer(), nullable=True),
        sa.Column("total_passes", sa.Integer(), nullable=True),
        sa.Column("offsides", sa.Integer(), nullable=True),
        sa.Column("attack_stats", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("passing_stats", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("defense_stats", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("duel_stats", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("discipline_stats", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("general_stats", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("starting_players", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("substitute_players", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("player_ratings", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("lineup_power_rating", sa.Float(), nullable=True),
        sa.Column("formation", sa.String(length=16), nullable=True),
        sa.Column("team_rating", sa.Float(), nullable=True),
        sa.Column("potm_player_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["potm_player_id"], ["players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", "team_id"),
    )
    op.create_table(
        "player_game_details",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(), nullable=True),
        sa.Column("minutes_played", sa.Integer(), nullable=True),
        sa.Column("is_starter", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("substitution_in_minute", sa.Integer(), nullable=True),
        sa.Column("substitution_out_minute", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("is_man_of_the_match", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("goals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assists", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shots_total", sa.Integer(), nullable=True),
        sa.Column("shots_on_target", sa.Integer(), nullable=True),
        sa.Column("expected_goals", sa.Float(), nullable=True),
        sa.Column("expected_goals_on_target", sa.Float(), nullable=True),
        sa.Column("expected_assists", sa.Float(), nullable=True),
        sa.Column("passes_completed", sa.Integer(), nullable=True),
        sa.Column("passes_attempted", sa.Integer(), nullable=True),
        sa.Column("pass_accuracy", sa.Float(), nullable=True),
        sa.Column("tackles", sa.Integer(), nullable=True),
        sa.Column("interceptions", sa.Integer(), nullable=True),
        sa.Column("clearances", sa.Integer(), nullable=True),
        sa.Column("shot_events", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("yellow_cards", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("red_cards", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fouls", sa.Integer(), nullable=True),
        sa.Column("season_average_rating", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["game_id", "team_id"], ["game_details.id", "game_details.team_id"], name="fk_player_game_details_game_details"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "id"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # Legacy FotMob DB는 002에서 rename만 적용됐으므로 001_init이 만든 테이블을 drop하지 않는다.
    if "manager" in inspector.get_table_names() or "bets" in inspector.get_table_names():
        return

    op.drop_table("player_game_details")
    op.drop_table("game_details")
    op.drop_table("game_infos")
    op.drop_index("ix_player_ratings_player_id", table_name="player_ratings")
    op.drop_table("player_ratings")
    op.drop_table("player_match_affect_features")
    op.drop_table("player_infos")
    op.drop_table("games")
    op.drop_table("players")
    op.drop_table("teams")
