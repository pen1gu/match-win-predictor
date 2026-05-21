"""Sofascore ingest / API smoke helpers (no DB required for parser checks)."""

from __future__ import annotations

import pandas as pd

from server.app.crawler.sofascore_page import PageMatchPayload
from server.app.integrations.sofascore_page_ingest import build_models_from_page_payload
from server.app.integrations.sofascore_ingest import build_models_from_schedule_row
from server.app.models.games.game_details import GameDetails
from server.app.models.games.game_infos import GameInfos
from server.app.models.players.player_game_details import PlayerGameDetails
from server.app.models.teams.team import Team
from sofascore_httpx.parsers import parse_event, parse_lineups

SAMPLE_EVENT = {
    "event": {
        "id": 10408559,
        "startTimestamp": 1660316400,
        "status": {"code": 100},
        "homeTeam": {"id": 2817, "name": "Osasuna"},
        "awayTeam": {"id": 2833, "name": "Sevilla"},
        "homeScore": {"current": 2},
        "awayScore": {"current": 1},
        "tournament": {"uniqueTournament": {"name": "La Liga"}},
        "season": {"year": "2022/2023"},
        "roundInfo": {"round": 1},
    }
}


def test_parse_event_sample() -> None:
    parsed = parse_event(SAMPLE_EVENT)
    assert parsed.game_id == 10408559
    assert parsed.home_team.name == "Osasuna"
    assert parsed.finished is True


def test_schedule_row_keeps_team_names_without_fake_ids() -> None:
    row = pd.Series(
        {
            "game_id": 10408559,
            "date": pd.Timestamp("2022-08-12 19:00:00", tz="UTC"),
            "home_team": "Osasuna",
            "away_team": "Sevilla",
            "home_score": 2,
            "away_score": 1,
            "round": 1,
        }
    )
    models = build_models_from_schedule_row(row, league="ESP-La Liga", season="2223")
    assert not any(isinstance(model, Team) for model in models)
    info = next(model for model in models if isinstance(model, GameInfos))
    assert info.home_team_id is None
    assert info.home_team_name == "Osasuna"


def test_lineup_parser_splits_substitutes() -> None:
    parsed = parse_lineups(
        {
            "home": {
                "team": {"id": 1},
                "formation": "4-3-3",
                "players": [
                    {"player": {"id": 10, "name": "Starter"}, "substitute": False},
                    {"player": {"id": 20, "name": "Sub"}, "substitute": True},
                ],
            }
        }
    )
    assert parsed.home is not None
    assert [p.player_id for p in parsed.home.starters] == [10]
    assert [p.player_id for p in parsed.home.substitutes] == [20]


def test_page_payload_builds_detail_models() -> None:
    payload = PageMatchPayload(
        game_id=10408559,
        url="https://www.sofascore.com/football/match/osasuna-sevilla/example#id:10408559",
        event=SAMPLE_EVENT,
        lineups={
            "home": {
                "team": {"id": 2817},
                "formation": "4-3-3",
                "players": [
                    {
                        "player": {"id": 10, "name": "Home Starter", "shirtNumber": 9},
                        "position": "F",
                        "substitute": False,
                        "statistics": {"rating": 7.1},
                    }
                ],
            },
            "away": {
                "team": {"id": 2833},
                "formation": "4-2-3-1",
                "players": [
                    {
                        "player": {"id": 20, "name": "Away Starter", "shirtNumber": 1},
                        "position": "G",
                        "substitute": False,
                    }
                ],
            },
        },
        statistics={"statistics": []},
        incidents={"incidents": []},
    )
    models = build_models_from_page_payload(payload)
    assert any(isinstance(model, Team) and model.id == 2817 for model in models)
    assert any(isinstance(model, GameDetails) and model.starting_players for model in models)
    assert any(isinstance(model, PlayerGameDetails) and model.id == 10 for model in models)


if __name__ == "__main__":
    test_parse_event_sample()
    test_schedule_row_keeps_team_names_without_fake_ids()
    test_lineup_parser_splits_substitutes()
    test_page_payload_builds_detail_models()
    print("predict_test OK")
