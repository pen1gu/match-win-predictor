from __future__ import annotations

import math
from typing import Literal

from server.app.models.games.game_details import GameDetails
from server.app.models.players.player import Player

PositionBucket = Literal["goalkeeper", "defender", "midfielder", "forward"]


def _position_bucket(player: Player) -> PositionBucket:
    position = None
    if player.info and player.info.position:
        position = player.info.position[0]
    elif player.game_details:
        position = player.game_details[0].position
    text = (position or "midfielder").lower()
    if "goal" in text or text in {"g", "gk"}:
        return "goalkeeper"
    if "def" in text or text in {"d", "cb", "lb", "rb"}:
        return "defender"
    if "forward" in text or "strik" in text or text in {"f", "st"}:
        return "forward"
    return "midfielder"


def compute_player_rating(player: Player) -> float:
    rating = 1500.0

    if player.info and player.info.current_market_value:
        rating += math.log10(max(player.info.current_market_value, 1)) * 50

    if player.info and player.info.age is not None:
        rating -= abs(player.info.age - 27) * 8

    if player.match_affect_features:
        features = player.match_affect_features
        status = (features.availability_status or "").lower()
        if any(word in status for word in ("injury", "injured", "suspend", "doubt")):
            rating -= 80
        if features.injury_history:
            rating -= min(len(features.injury_history) * 15, 120)
        if features.form_rating is not None:
            rating += (features.form_rating - 6.5) * 40

    if player.info and player.info.fan_rating is not None:
        rating += (player.info.fan_rating - 6.5) * 30

    recent = sorted(player.game_details or [], key=lambda d: d.game_id, reverse=True)[:5]
    if recent:
        ratings = [d.rating for d in recent if d.rating is not None]
        if ratings and not (player.match_affect_features and player.match_affect_features.form_rating):
            rating += (sum(ratings) / len(ratings) - 6.5) * 35

        bucket = _position_bucket(player)
        per90_attack = sum((d.goals or 0) + (d.expected_goals or 0) for d in recent) / max(len(recent), 1)
        per90_defense = sum((d.tackles or 0) + (d.interceptions or 0) for d in recent) / max(len(recent), 1)
        if bucket == "forward":
            rating += per90_attack * 25
        elif bucket == "midfielder":
            rating += per90_attack * 15 + per90_defense * 10
        elif bucket == "defender":
            rating += per90_defense * 20
        elif bucket == "goalkeeper":
            rating += per90_defense * 15

    return max(900.0, min(2300.0, rating))


def compute_lineup_features(players: list[Player], *, is_home: bool = True) -> dict[str, float]:
    if not players:
        return {"total_rating": 1500.0, "attack": 0.0, "defense": 0.0}

    ratings = [compute_player_rating(p) for p in players]
    while len(ratings) < 11:
        avg = sum(ratings) / len(ratings)
        ratings.append(avg)

    attack_weight = {"forward": 1.2, "midfielder": 0.9, "defender": 0.5, "goalkeeper": 0.2}
    defense_weight = {"forward": 0.3, "midfielder": 0.7, "defender": 1.2, "goalkeeper": 1.3}

    attack = 0.0
    defense = 0.0
    for player, rating in zip(players, ratings[:11], strict=False):
        bucket = _position_bucket(player)
        attack += rating * attack_weight[bucket]
        defense += rating * defense_weight[bucket]

    home_bonus = 30.0 if is_home else 0.0
    return {
        "total_rating": sum(ratings[:11]) + home_bonus,
        "attack": attack,
        "defense": defense,
    }


def _softmax(values: list[float]) -> list[float]:
    max_v = max(values)
    exps = [math.exp(v - max_v) for v in values]
    total = sum(exps)
    return [e / total for e in exps]


def get_historical_win_rate(details: list[GameDetails], *, is_home_perspective: bool) -> float:
    if not details:
        return 0.33
    wins = 0
    for row in details[:10]:
        if row.score is None:
            continue
        if row.is_home == is_home_perspective and row.score > 0:
            wins += 1
        elif row.is_home != is_home_perspective and row.score == 0:
            wins += 1
    return wins / max(min(len(details), 10), 1)


def predict_match_outcomes(
    home_players: list[Player],
    away_players: list[Player],
    *,
    home_history: list[GameDetails] | None = None,
    away_history: list[GameDetails] | None = None,
) -> dict[str, float]:
    home_features = compute_lineup_features(home_players, is_home=True)
    away_features = compute_lineup_features(away_players, is_home=False)

    home_hist = get_historical_win_rate(home_history or [], is_home_perspective=True)
    away_hist = get_historical_win_rate(away_history or [], is_home_perspective=False)

    logits = [
        0.001 * home_features["total_rating"] + 0.8 * home_hist + 0.0005 * home_features["attack"],
        -0.2,
        0.001 * away_features["total_rating"] + 0.8 * away_hist + 0.0005 * away_features["attack"],
    ]
    probs = _softmax(logits)
    return {"home": probs[0], "draw": probs[1], "away": probs[2]}
