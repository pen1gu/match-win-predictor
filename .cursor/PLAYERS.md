# 선수 rating 평가 규칙

fotmob API 응답 기준으로 추출 가능한 선수 rating 구성 요소 정의.
이 문서는 **API에서 추출 가능한 요소 후보**를 정리하는 용도이며, 현재 구현(`compute_player_rating()`)과는 분리해서 관리한다.

---

## 확장 가능한 요소 목록

### 기본 프로필

| 요소 | JSON 경로 | 비고 |
|------|-----------|------|
| 나이 | `playerInformation[age].numberValue` | 피크 나이(26~29) 가산, 노장/신예 감산 |
| 포지션 | `positionDescription.primaryPosition.key` | ST/CF/LW/RW/CM/CB/GK 구분 |
| 선호 발 | `playerInformation[preferred_foot].key` | right/left/both |
| 키 | `playerInformation[height].numberValue` | 헤딩 강점 판단 보조 (cm) |
| 주장 여부 | `isCaptain` | bool, 팀 내 영향력 보정 |
| 부상 여부 | `injuryInformation` | null이면 정상, 객체이면 부상 중 → 등급 하락 |
| 계약 잔여 기간 | `contractEnd.utcTime` | 남은 개월 수 → 의욕/안정성 보정 |

---

### 현재 시즌 스탯 (`mainLeague.stats`)

| 요소 | localizedTitleId | 설명 |
|------|-----------------|------|
| 골 | `goals` | 시즌 총 득점 |
| 어시스트 | `assists` | 시즌 총 어시스트 |
| 출전 수 | `matches_uppercase` | 전체 출전 경기 수 |
| 선발 수 | `started` | 선발 출전 수 |
| 출전 시간 | `minutes_played` | 총 출전 분 |
| 평점 | `rating` | fotmob 시즌 평균 평점 |
| 경고 | `yellow_cards` | 누적 경고 수 |
| 퇴장 | `red_cards` | 퇴장 횟수 |

---

### 심층 스탯 (`firstSeasonStats.statsSection`) — 포지션별 가중치 차등

#### 슈팅 (Shooting)

| 요소 | localizedTitleId | per90 활용 여부 |
|------|-----------------|---------------|
| xG | `expected_goals` | ✅ |
| xGOT | `expected_goals_on_target` | ✅ |
| 슛 시도 | `shots` | ✅ |
| 유효 슛 | `ShotsOnTarget` | ✅ |
| 헤딩 슛 | `headed_shots` | ✅ |
| 패널티 골 | `goals_subtitle` | 선택 |
| 비패널티 xG | `non_penalty_xg` | ✅ |
| percentileRank | 각 스탯의 `percentileRank` | 다른 포워드 대비 상대 위치 (0~100) |

#### 패스·찬스 창출 (Passing)

| 요소 | localizedTitleId | 비고 |
|------|-----------------|------|
| xA | `expected_assists` | 어시스트 기대값 |
| 찬스 창출 | `chances_created` | 슈팅 기회 제공 횟수 |
| 빅찬스 창출 | `big_chance_created_team_title` | 고xG 찬스 창출 |
| 패스 정확도 | `successful_passes_accuracy` | % |
| 크로스 정확도 | `crosses_succeeeded_accuracy` | % |

#### 점유·볼 키핑 (Possession)

| 요소 | localizedTitleId | 비고 |
|------|-----------------|------|
| 드리블 성공 | `dribbles_succeeded` | 횟수 |
| 드리블 성공률 | `won_contest_subtitle` | % |
| 공중볼 승리 | `aerials_won` | 횟수 |
| 공중볼 승률 | `aerials_won_percent` | % |
| 상대 박스 터치 | `touches_opp_box` | 공격 위협 지표 |
| 볼 빼앗김 | `dispossessed` | 낮을수록 좋음 |
| 파울 획득 | `fouls_won` | 파울 유도 능력 |

#### 수비 기여 (Defending)

| 요소 | localizedTitleId | 비고 |
|------|-----------------|------|
| 수비 액션 | `defensive_actions` | 태클 + 인터셉트 합산 |
| 볼 탈취(공격 3분의1) | `poss_won_att_3rd_team_title` | 전방 압박 지표 |
| 리커버리 | `recoveries` | 루즈볼 회수 |

#### 징계 (Discipline)

| 요소 | localizedTitleId | 비고 |
|------|-----------------|------|
| 경고 | `yellow_cards` | per90 기준 감산 |
| 퇴장 | `red_cards` | per90 기준 감산 |

---

### 최근 경기 폼 (`recentMatches`)

각 경기에서 추출 가능한 세부 요소:

| 요소 | 경로 | 활용 방식 |
|------|------|----------|
| 경기 평점 | `ratingProps.rating` | 최근 N경기 가중 평균 (최신 경기 가중치 높게) |
| 맨 오브 더 매치 | `playerOfTheMatch` | 횟수 보정 (+) |
| 최고 평점 여부 | `ratingProps.isTopRating` | bool, 팀 내 최우수 |
| 골/어시스트 | `goals`, `assists` | 직접 기여 |
| 경고/퇴장 | `yellowCards`, `redCards` | 감산 |
| 출전 시간 | `minutesPlayed` | 0분(벤치)이면 폼 계산 제외 |
| 홈/원정 | `isHomeTeam` | 원정 고득점 가산 |
| 리그 수준 | `leagueId` / `leagueName` | UCL·PL 경기 가중치 > 컵 경기 |
| 토너먼트 스테이지 | `stage` | final/1/8 등 → 중요도 계수 |

---

### 커리어 및 시즌별 평점 (`careerHistory.seasonEntries`)

| 요소 | 경로 | 활용 방식 |
|------|------|----------|
| 시즌 평균 평점 | `seasonEntries[].rating.rating` | 최근 3시즌 가중 평균 |
| 리그 수준 보정 | `seasonEntries[].tournamentStats[].leagueName` | PL/UCL > 2부 리그 등 계수 적용 |
| 90분당 득점 | `goals / appearances` | 절대 수치보다 per90 권장 |
| 출전 지속성 | `appearances` | 풀시즌(30+경기) 여부 |

---

### 트레이트 (포지션 대비 상대 점수)

`traits.items[]` — 같은 포지션 선수 대비 0~1 스케일:

| 요소 | key | 비고 |
|------|-----|------|
| 찬스 창출 | `chances_created` | 0.59 (중상위) |
| 공중볼 | `aerials_won` | 0.21 (하위) |
| 수비 기여 | `defensive_actions` | 0.21 (하위) |
| 골 | `goals` | 0.89 (최상위) |
| 슈팅 시도 | `shot_attempts` | 0.57 (중위) |
| 터치 수 | `touches` | 0.26 (하위 — ST 특성) |

이 값들은 포지션 내 상대 퍼포먼스를 빠르게 판단할 때 사용한다.

---

### 숏맵 기반 슈팅 패턴 (`firstSeasonStats.shotmap`)

개별 슈팅 이벤트에서 추출 가능한 요소:

| 요소 | 경로 | 활용 방식 |
|------|------|----------|
| 슛 유형 | `shotType` | RightFoot/LeftFoot/Header 비율 |
| 상황 | `situation` | RegularPlay/Penalty/FastBreak/SetPiece/FromCorner |
| 박스 내/외 | `isFromInsideBox` | 박스 내 슈팅 비율 → 마무리 위치 선정 |
| xG | `expectedGoals` | 슛별 골 기대값 합산 |
| xGOT | `expectedGoalsOnTarget` | 유효 슛 기준 골 기대값 |
| 이벤트 결과 | `eventType` | Goal/AttemptSaved/Miss/Post |

---

## 3. 우선순위 정리 (현재 구현 기준)

```
compute_player_rating() 반영 순서:
1. 시장 가치          ← current_market_value
2. 최근 폼 평점       ← form_rating (recentMatches 평균)
3. 시즌/커리어 평점    ← fan_rating (seasonEntries 평균)

미반영(확장 후보):
- per90 슛·xG·xA
- 공중볼 승률 (포지션별 보정)
- 최근 N경기 맨 오브 더 매치 횟수
- 리그 수준 계수 (UCL vs 컵 경기 구분)
- 부상 여부 즉시 감산
- 경고 누적 패널티
```
