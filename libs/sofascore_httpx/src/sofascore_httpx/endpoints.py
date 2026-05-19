SOFASCORE_API_BASE = "https://api.sofascore.com/api/v1"


def event(game_id: int) -> str:
    return f"{SOFASCORE_API_BASE}/event/{game_id}"


def lineups(game_id: int) -> str:
    return f"{SOFASCORE_API_BASE}/event/{game_id}/lineups"


def statistics(game_id: int) -> str:
    return f"{SOFASCORE_API_BASE}/event/{game_id}/statistics"


def incidents(game_id: int) -> str:
    return f"{SOFASCORE_API_BASE}/event/{game_id}/incidents"


def player_statistics(game_id: int, player_id: int) -> str:
    return f"{SOFASCORE_API_BASE}/event/{game_id}/player/{player_id}/statistics"
