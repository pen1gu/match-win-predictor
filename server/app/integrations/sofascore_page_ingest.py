from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sofascore_httpx.parsers import (
    parse_event,
    parse_incidents,
    parse_lineups,
    parse_player_stats,
    parse_team_stats,
)

from server.app.crawler.sofascore_page import (
    PageMatchPayload,
    SofascorePageCrawler,
    SofascorePageCrawlerSession,
)
from server.app.integrations.sofascore_ingest import (
    _apply_parsed_player_stats,
    _apply_team_stats,
    _lineup_side_models,
    _merge_game_details,
)
from server.app.models.games.game import Game
from server.app.models.games.game_details import GameDetails
from server.app.models.games.game_infos import GameInfos
from server.app.models.players.player_game_details import PlayerGameDetails
from server.app.models.teams.team import Team
from server.app.tasks.ingest_helpers import extract_season_label


def _find_dict_with_event_id(value: Any, game_id: int) -> dict[str, Any] | None:
    if isinstance(value, dict):
        event = value.get("event")
        if isinstance(event, dict) and int(event.get("id") or 0) == game_id:
            return value
        if int(value.get("id") or 0) == game_id and value.get("homeTeam") and value.get("awayTeam"):
            return value
        for child in value.values():
            found = _find_dict_with_event_id(child, game_id)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_dict_with_event_id(item, game_id)
            if found:
                return found
    return None


def _event_raw(payload: PageMatchPayload) -> dict[str, Any]:
    if payload.event:
        found = _find_dict_with_event_id(payload.event, payload.game_id)
        if found:
            return found
    if payload.cached_event:
        found = _find_dict_with_event_id(payload.cached_event, payload.game_id)
        if found:
            return found
    for item in payload.embedded_json:
        found = _find_dict_with_event_id(item, payload.game_id)
        if found:
            return found
    raise ValueError(f"event data not found in page crawl payload: game_id={payload.game_id}")


def build_models_from_page_payload(payload: PageMatchPayload) -> list[Any]:
    event = parse_event(_event_raw(payload))
    lineups = parse_lineups(payload.lineups or {})
    team_stats = parse_team_stats(payload.statistics or {})
    incidents = parse_incidents(payload.incidents or {})

    game_id = payload.game_id
    home_team_id = event.home_team.id
    away_team_id = event.away_team.id
    match_date = event.start_timestamp or datetime.now(tz=timezone.utc)
    season_label = extract_season_label(event.season_name)

    models: list[Any] = [
        Team(id=home_team_id, name=event.home_team.name, league=event.league_name),
        Team(id=away_team_id, name=event.away_team.name, league=event.league_name),
        Game(id=game_id),
        GameInfos(
            id=game_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team_name=event.home_team.name,
            away_team_name=event.away_team.name,
            match_date=match_date,
            match_name=f"{event.home_team.name} - {event.away_team.name}",
            league_name=event.league_name,
            season=season_label,
            match_round=event.round_name,
            stadium=event.stadium,
            referee=event.referee,
            finished=event.finished,
            cancelled=event.cancelled,
            next_match=not event.finished,
            events=incidents,
        ),
    ]

    home_detail = GameDetails(
        id=game_id,
        team_id=home_team_id,
        is_home=True,
        score=event.home_score or 0,
    )
    away_detail = GameDetails(
        id=game_id,
        team_id=away_team_id,
        is_home=False,
        score=event.away_score or 0,
    )
    _apply_team_stats(home_detail, away_detail, team_stats)
    models.extend([home_detail, away_detail])

    home_lineup_detail, home_extras = _lineup_side_models(
        game_id,
        lineups.home,
        is_home=True,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
    )
    away_lineup_detail, away_extras = _lineup_side_models(
        game_id,
        lineups.away,
        is_home=False,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
    )
    if home_lineup_detail:
        _merge_game_details(home_detail, home_lineup_detail)
    if away_lineup_detail:
        _merge_game_details(away_detail, away_lineup_detail)

    models.extend(home_extras)
    models.extend(away_extras)

    by_player: dict[int, PlayerGameDetails] = {
        model.id: model for model in models if isinstance(model, PlayerGameDetails)
    }
    for player_id, raw in payload.player_statistics.items():
        target = by_player.get(player_id)
        if target is None:
            continue
        _apply_parsed_player_stats(target, parse_player_stats(raw, player_id))

    return models


async def build_models_from_page_crawl(
    game_id: int,
    *,
    league: str | None = None,
    season: str | None = None,
    crawler: SofascorePageCrawler | SofascorePageCrawlerSession | None = None,
) -> list[Any]:
    if crawler is None:
        crawler = SofascorePageCrawler()
    payload = await crawler.fetch_match(game_id, league=league, season=season)
    return build_models_from_page_payload(payload)
