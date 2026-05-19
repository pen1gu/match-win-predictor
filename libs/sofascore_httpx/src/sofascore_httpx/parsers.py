from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ParsedTeamRef:
    id: int
    name: str


@dataclass
class ParsedEvent:
    game_id: int
    home_team: ParsedTeamRef
    away_team: ParsedTeamRef
    home_score: int | None
    away_score: int | None
    start_timestamp: datetime | None
    league_name: str | None
    season_name: str | None
    round_name: str | None
    finished: bool
    cancelled: bool
    stadium: str | None = None
    referee: str | None = None


@dataclass
class ParsedLineupPlayer:
    player_id: int
    name: str
    position: str | None
    shirt_number: int | None
    is_starter: bool
    rating: float | None = None


@dataclass
class ParsedLineupSide:
    team_id: int
    formation: str | None
    starters: list[ParsedLineupPlayer] = field(default_factory=list)
    substitutes: list[ParsedLineupPlayer] = field(default_factory=list)


@dataclass
class ParsedLineups:
    home: ParsedLineupSide | None
    away: ParsedLineupSide | None


@dataclass
class ParsedTeamStatSide:
    team_id: int
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedTeamStats:
    home: ParsedTeamStatSide | None
    away: ParsedTeamStatSide | None


@dataclass
class ParsedPlayerStats:
    player_id: int
    rating: float | None = None
    minutes_played: int | None = None
    goals: int = 0
    assists: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _team_ref(team: dict[str, Any] | None) -> ParsedTeamRef | None:
    if not team:
        return None
    team_id = team.get("id")
    name = team.get("name") or team.get("shortName") or ""
    if team_id is None:
        return None
    return ParsedTeamRef(id=int(team_id), name=str(name))


def _score(side: dict[str, Any] | None) -> int | None:
    if not side:
        return None
    current = side.get("current")
    if current is None:
        display = side.get("display")
        if display is not None:
            try:
                return int(display)
            except (TypeError, ValueError):
                return None
        return None
    try:
        return int(current)
    except (TypeError, ValueError):
        return None


def parse_event(raw: dict[str, Any]) -> ParsedEvent:
    event = raw.get("event") or raw
    game_id = int(event["id"])
    status = event.get("status") or {}
    code = status.get("code", 0)
    finished = code == 100
    cancelled = code in {70, 90, 120}

    ts = event.get("startTimestamp")
    start_dt = (
        datetime.fromtimestamp(int(ts), tz=timezone.utc) if ts is not None else None
    )

    tournament = event.get("tournament") or {}
    unique = tournament.get("uniqueTournament") or {}
    season = event.get("season") or {}
    round_info = event.get("roundInfo") or {}

    venue = event.get("venue") or {}
    stadium = venue.get("name") or venue.get("stadium", {}).get("name")
    referee = (event.get("referee") or {}).get("name")

    home = _team_ref(event.get("homeTeam"))
    away = _team_ref(event.get("awayTeam"))
    if home is None or away is None:
        raise ValueError(f"Missing teams in event {game_id}")

    return ParsedEvent(
        game_id=game_id,
        home_team=home,
        away_team=away,
        home_score=_score(event.get("homeScore")),
        away_score=_score(event.get("awayScore")),
        start_timestamp=start_dt,
        league_name=unique.get("name") or tournament.get("name"),
        season_name=season.get("name") or season.get("year"),
        round_name=str(round_info.get("round") or round_info.get("name") or ""),
        finished=finished,
        cancelled=cancelled,
        stadium=stadium,
        referee=referee,
    )


def _parse_lineup_side(side: dict[str, Any] | None) -> ParsedLineupSide | None:
    if not side:
        return None
    team = side.get("team") or {}
    team_id = team.get("id")
    if team_id is None:
        return None

    def _players(items: list[dict[str, Any]] | None, *, starter: bool) -> list[ParsedLineupPlayer]:
        result: list[ParsedLineupPlayer] = []
        for item in items or []:
            is_substitute = bool(item.get("substitute"))
            if starter and is_substitute:
                continue
            if not starter and not is_substitute:
                continue
            player = item.get("player") or item
            pid = player.get("id")
            if pid is None:
                continue
            stats = item.get("statistics") or player.get("statistics") or {}
            rating = stats.get("rating")
            result.append(
                ParsedLineupPlayer(
                    player_id=int(pid),
                    name=str(player.get("name") or player.get("shortName") or ""),
                    position=item.get("position") or player.get("position"),
                    shirt_number=player.get("shirtNumber") or item.get("shirtNumber"),
                    is_starter=starter,
                    rating=float(rating) if rating is not None else None,
                )
            )
        return result

    return ParsedLineupSide(
        team_id=int(team_id),
        formation=side.get("formation"),
        starters=_players(side.get("players") or side.get("starters"), starter=True),
        substitutes=_players(
            side.get("substitutes") if side.get("substitutes") is not None else side.get("players"),
            starter=False,
        ),
    )


def parse_lineups(raw: dict[str, Any]) -> ParsedLineups:
    home = raw.get("home") or raw.get("homeTeam")
    away = raw.get("away") or raw.get("awayTeam")
    return ParsedLineups(
        home=_parse_lineup_side(home),
        away=_parse_lineup_side(away),
    )


def _flatten_stat_groups(groups: list[dict[str, Any]] | None) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for group in groups or []:
        for item in group.get("statisticsItems") or group.get("statistics") or []:
            key = item.get("key") or item.get("name")
            if not key:
                continue
            flat[str(key)] = _first_present(item.get("value"), item.get("homeValue"))
            flat[f"{key}_home"] = item.get("homeValue")
            flat[f"{key}_away"] = item.get("awayValue")
    return flat


def parse_team_stats(raw: dict[str, Any]) -> ParsedTeamStats:
    statistics = raw.get("statistics") or []
    home_stats: dict[str, Any] = {}
    away_stats: dict[str, Any] = {}
    home_id: int | None = None
    away_id: int | None = None

    for period in statistics:
        if period.get("period") not in (None, "ALL", "all", "FullTime"):
            continue
        for group in period.get("groups") or []:
            for item in group.get("statisticsItems") or []:
                key = str(item.get("key") or item.get("name") or "")
                if not key:
                    continue
                home_stats[key] = _first_present(item.get("homeValue"), item.get("home"))
                away_stats[key] = _first_present(item.get("awayValue"), item.get("away"))

    # team ids sometimes in root
    if raw.get("homeTeam"):
        home_id = raw["homeTeam"].get("id")
    if raw.get("awayTeam"):
        away_id = raw["awayTeam"].get("id")

    return ParsedTeamStats(
        home=ParsedTeamStatSide(int(home_id), home_stats) if home_id else ParsedTeamStatSide(0, home_stats),
        away=ParsedTeamStatSide(int(away_id), away_stats) if away_id else ParsedTeamStatSide(0, away_stats),
    )


def parse_incidents(raw: dict[str, Any]) -> list[dict[str, Any]]:
    incidents = raw.get("incidents") or raw.get("events") or []
    return [dict(item) for item in incidents]


def parse_player_stats(raw: dict[str, Any], player_id: int) -> ParsedPlayerStats:
    stats_root = raw.get("statistics") or raw.get("playerStatistics") or raw
    groups = stats_root if isinstance(stats_root, list) else stats_root.get("groups") or []
    flat = _flatten_stat_groups(groups if isinstance(groups, list) else [groups])

    rating = flat.get("rating")
    minutes = flat.get("minutesPlayed") or flat.get("minutes_played")

    return ParsedPlayerStats(
        player_id=player_id,
        rating=float(rating) if rating is not None else None,
        minutes_played=int(minutes) if minutes is not None else None,
        goals=int(flat.get("goals") or 0),
        assists=int(flat.get("goalAssist") or flat.get("assists") or 0),
        raw=flat,
    )
