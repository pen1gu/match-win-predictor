const API_BASE = window.__API_BASE__ || "";

function apiUrl(path) {
  return `${API_BASE}${path}`;
}

function setStatus(message, isError = false) {
  const el = document.getElementById("status");
  el.textContent = message;
  el.className = isError ? "status error" : "status";
}

function formatPct(value) {
  if (value == null) return "-";
  return `${(value * 100).toFixed(1)}%`;
}

function renderGame(game) {
  const card = document.createElement("article");
  card.className = "card";
  const scoreHome = game.score?.home ?? "-";
  const scoreAway = game.score?.away ?? "-";
  let outcomesHtml = "";
  if (game.outcomes) {
    outcomesHtml = `
      <div class="outcomes">
        <span>홈 ${formatPct(game.outcomes.home)}</span>
        <span>무 ${formatPct(game.outcomes.draw)}</span>
        <span>원정 ${formatPct(game.outcomes.away)}</span>
      </div>`;
  }
  card.innerHTML = `
    <h2>${game.home_team} vs ${game.away_team}</h2>
    <div class="meta">game_id: ${game.game_id} · ${game.league_name || ""} · ${game.match_round || ""}</div>
    <div class="meta">${new Date(game.match_date).toLocaleString()} · ${game.finished ? "종료" : "예정"}</div>
    <div>스코어: ${scoreHome} - ${scoreAway}</div>
    ${outcomesHtml}
  `;
  return card;
}

async function loadGames() {
  const limit = document.getElementById("limit").value;
  const includeOutcomes = document.getElementById("includeOutcomes").checked;
  setStatus("로딩 중...");
  const params = new URLSearchParams({ limit, include_outcomes: includeOutcomes });
  try {
    const res = await fetch(apiUrl(`/api/v1/games/latest?${params}`));
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    const container = document.getElementById("games");
    container.innerHTML = "";
    data.games.forEach((game) => container.appendChild(renderGame(game)));
    setStatus(`${data.count}경기 표시`);
  } catch (err) {
    setStatus(`데이터 로드 실패: ${err.message}`, true);
  }
}

document.getElementById("refreshBtn").addEventListener("click", loadGames);
loadGames();
