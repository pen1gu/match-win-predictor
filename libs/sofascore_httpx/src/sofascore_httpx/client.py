from __future__ import annotations

import asyncio
from typing import Any

import tls_requests

from sofascore_httpx import endpoints
from sofascore_httpx.parsers import (
    ParsedEvent,
    ParsedLineups,
    ParsedPlayerStats,
    ParsedTeamStats,
    parse_event,
    parse_incidents,
    parse_lineups,
    parse_player_stats,
    parse_team_stats,
)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class SofascoreClient:
    """Sofascore API client (tls_requests — plain httpx는 403)."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._headers = {**DEFAULT_HEADERS, **(headers or {})}

    def _request_json(self, url: str) -> dict[str, Any]:
        response = tls_requests.get(url, headers=self._headers, timeout=self._timeout)
        if response.status_code >= 400:
            raise RuntimeError(f"Sofascore HTTP {response.status_code}: {url}")
        data = response.json()
        if isinstance(data, dict):
            return data
        return {"data": data}

    async def _get_json(self, url: str) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                return await asyncio.to_thread(self._request_json, url)
            except (RuntimeError, ValueError, TypeError) as exc:
                last_exc = exc
                if attempt + 1 < self._max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"Sofascore request failed: {url}") from last_exc

    async def get_event_raw(self, game_id: int) -> dict[str, Any]:
        return await self._get_json(endpoints.event(game_id))

    async def get_lineups_raw(self, game_id: int) -> dict[str, Any]:
        return await self._get_json(endpoints.lineups(game_id))

    async def get_statistics_raw(self, game_id: int) -> dict[str, Any]:
        return await self._get_json(endpoints.statistics(game_id))

    async def get_incidents_raw(self, game_id: int) -> dict[str, Any]:
        return await self._get_json(endpoints.incidents(game_id))

    async def get_player_statistics_raw(self, game_id: int, player_id: int) -> dict[str, Any]:
        return await self._get_json(endpoints.player_statistics(game_id, player_id))

    async def get_event(self, game_id: int) -> ParsedEvent:
        return parse_event(await self.get_event_raw(game_id))

    async def get_lineups(self, game_id: int) -> ParsedLineups:
        return parse_lineups(await self.get_lineups_raw(game_id))

    async def get_team_stats(self, game_id: int) -> ParsedTeamStats:
        return parse_team_stats(await self.get_statistics_raw(game_id))

    async def get_incidents(self, game_id: int) -> list[dict[str, Any]]:
        return parse_incidents(await self.get_incidents_raw(game_id))

    async def get_player_stats(self, game_id: int, player_id: int) -> ParsedPlayerStats:
        raw = await self.get_player_statistics_raw(game_id, player_id)
        return parse_player_stats(raw, player_id)
