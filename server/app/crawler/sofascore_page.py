from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext, Page, Response, async_playwright

from server.config.settings import settings
from server.utils.logger.get_logger import get_logger

logger = get_logger(__name__)

SOFASCORE_BASE_URL = "https://www.sofascore.com"


@dataclass
class PageMatchPayload:
    game_id: int
    url: str
    cached_event: dict[str, Any] | None = None
    event: dict[str, Any] | None = None
    lineups: dict[str, Any] | None = None
    statistics: dict[str, Any] | None = None
    incidents: dict[str, Any] | None = None
    player_statistics: dict[int, dict[str, Any]] = field(default_factory=dict)
    embedded_json: list[dict[str, Any]] = field(default_factory=list)
    html: str | None = None


def _compact_season(season: str | None) -> str | None:
    if not season:
        return None
    match = re.match(r"^(\d{2,4})/(\d{2,4})$", season)
    if not match:
        return None
    return f"{match.group(1)[-2:]}{match.group(2)[-2:]}"


def _cached_round_files(league: str | None, season: str | None) -> list[Path]:
    data_dir = Path(settings.sofascore_data_dir) / "matches"
    if not data_dir.exists():
        return []
    compact = _compact_season(season)
    if league and compact:
        return list(data_dir.glob(f"round_matches_{league}_{compact}_*.json"))
    return list(data_dir.glob("round_matches_*.json"))


def _url_from_cached_event(event: dict[str, Any], game_id: int) -> str | None:
    slug = event.get("slug")
    custom_id = event.get("customId")
    if slug and custom_id:
        return f"{SOFASCORE_BASE_URL}/football/match/{slug}/{custom_id}#id:{game_id}"
    return None


def find_cached_event(
    game_id: int,
    *,
    league: str | None = None,
    season: str | None = None,
) -> dict[str, Any] | None:
    for path in _cached_round_files(league, season):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for event in data.get("events") or []:
            if int(event.get("id") or 0) != game_id:
                continue
            return dict(event)
    return None


def resolve_sofascore_match_url(
    game_id: int,
    *,
    league: str | None = None,
    season: str | None = None,
) -> str:
    cached_event = find_cached_event(game_id, league=league, season=season)
    if cached_event:
        resolved = _url_from_cached_event(cached_event, game_id)
        if resolved:
            return resolved
    return f"{SOFASCORE_BASE_URL}/event/{game_id}"


def _json_kind(url: str, game_id: int) -> tuple[str, int | None] | None:
    if f"/event/{game_id}" not in url:
        return None
    if re.search(rf"/event/{game_id}/player/(\d+)/statistics", url):
        player_id = int(re.search(rf"/event/{game_id}/player/(\d+)/statistics", url).group(1))  # type: ignore[union-attr]
        return "player_statistics", player_id
    if url.rstrip("/").endswith(f"/event/{game_id}"):
        return "event", None
    if f"/event/{game_id}/lineups" in url:
        return "lineups", None
    if f"/event/{game_id}/statistics" in url:
        return "statistics", None
    if f"/event/{game_id}/incidents" in url:
        return "incidents", None
    return None


def _has_event_id(data: dict[str, Any], game_id: int) -> bool:
    event = data.get("event") if isinstance(data.get("event"), dict) else data
    try:
        return int(event.get("id") or 0) == game_id
    except (AttributeError, TypeError, ValueError):
        return False


def _embedded_json_from_html(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    payloads: list[dict[str, Any]] = []
    for script in soup.find_all("script"):
        text = script.string or script.get_text()
        if not text:
            continue
        text = text.strip()
        if not (text.startswith("{") or text.startswith("[")):
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            payloads.append(value)
    return payloads


class SofascorePageCrawler:
    def __init__(
        self,
        *,
        headless: bool = True,
        timeout_ms: int = 45_000,
        wait_after_load_ms: int = 2_000,
    ) -> None:
        self._headless = headless
        self._timeout_ms = timeout_ms
        self._wait_after_load_ms = wait_after_load_ms

    async def fetch_match(
        self,
        game_id: int,
        *,
        league: str | None = None,
        season: str | None = None,
        context: BrowserContext | None = None,
    ) -> PageMatchPayload:
        cached_event = find_cached_event(game_id, league=league, season=season)
        url = resolve_sofascore_match_url(game_id, league=league, season=season)
        if context is not None:
            return await self._fetch_with_context(context, game_id, url, cached_event)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self._headless)
            try:
                browser_context = await browser.new_context(
                    user_agent=settings.user_agent,
                    locale="en-US",
                    timezone_id="UTC",
                )
                return await self._fetch_with_context(browser_context, game_id, url, cached_event)
            finally:
                try:
                    await browser.close()
                except Exception as exc:
                    logger.debug("browser close failed: %s", exc)

    async def _fetch_with_context(
        self,
        context: BrowserContext,
        game_id: int,
        url: str,
        cached_event: dict[str, Any] | None,
    ) -> PageMatchPayload:
        page = await context.new_page()
        page.set_default_timeout(self._timeout_ms)
        payload = PageMatchPayload(game_id=game_id, url=url, cached_event=cached_event)
        response_tasks: list[asyncio.Task[None]] = []

        async def handle_response(response: Response) -> None:
            kind = _json_kind(response.url, game_id)
            if kind is None:
                return
            try:
                data = await response.json()
            except Exception:
                return
            name, player_id = kind
            if name == "player_statistics" and player_id is not None:
                payload.player_statistics[player_id] = data
            elif name == "event" and not _has_event_id(data, game_id):
                logger.debug(
                    "skip non-event JSON for game_id=%s url=%s keys=%s",
                    game_id,
                    response.url,
                    list(data)[:10],
                )
            else:
                setattr(payload, name, data)

        page.on(
            "response",
            lambda response: response_tasks.append(asyncio.create_task(handle_response(response))),
        )

        logger.info("page crawl start: game_id=%s url=%s", game_id, url)
        await page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
        await self._dismiss_overlays(page)
        await self._open_data_tabs(page)
        await page.wait_for_timeout(self._wait_after_load_ms)
        if response_tasks:
            await asyncio.gather(*response_tasks, return_exceptions=True)
        payload.html = await page.content()
        payload.embedded_json = _embedded_json_from_html(payload.html)
        await page.close()
        logger.info(
            "page crawl done: game_id=%s event=%s lineups=%s stats=%s incidents=%s player_stats=%d",
            game_id,
            bool(payload.event),
            bool(payload.lineups),
            bool(payload.statistics),
            bool(payload.incidents),
            len(payload.player_statistics),
        )
        return payload

    async def _dismiss_overlays(self, page: Page) -> None:
        for text in ("Accept", "I agree", "Agree", "Got it"):
            try:
                await page.get_by_text(text, exact=True).click(timeout=1_000)
                return
            except Exception:
                continue

    async def _open_data_tabs(self, page: Page) -> None:
        for text in ("Lineups", "Statistics", "Stats", "Details"):
            try:
                await page.get_by_text(text, exact=True).first.click(timeout=2_000)
                await page.wait_for_timeout(1_000)
            except Exception:
                continue


class SofascorePageCrawlerSession:
    """Reuse one browser for many match pages (faster and more stable than per-match launch)."""

    def __init__(
        self,
        *,
        headless: bool = True,
        timeout_ms: int = 45_000,
        wait_after_load_ms: int = 2_000,
    ) -> None:
        self._crawler = SofascorePageCrawler(
            headless=headless,
            timeout_ms=timeout_ms,
            wait_after_load_ms=wait_after_load_ms,
        )
        self._pw = None
        self._browser = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> SofascorePageCrawlerSession:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self._crawler._headless)
        self._context = await self._browser.new_context(
            user_agent=settings.user_agent,
            locale="en-US",
            timezone_id="UTC",
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._context is not None:
            try:
                await self._context.close()
            except Exception as exc:
                logger.debug("context close failed: %s", exc)
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception as exc:
                logger.debug("browser close failed: %s", exc)
        if self._pw is not None:
            try:
                await self._pw.stop()
            except Exception as exc:
                logger.debug("playwright stop failed: %s", exc)
        self._context = None
        self._browser = None
        self._pw = None

    async def fetch_match(
        self,
        game_id: int,
        *,
        league: str | None = None,
        season: str | None = None,
    ) -> PageMatchPayload:
        if self._context is None:
            raise RuntimeError("SofascorePageCrawlerSession is not started; use async with")
        return await self._crawler.fetch_match(
            game_id,
            league=league,
            season=season,
            context=self._context,
        )
