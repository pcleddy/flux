# Flux — Full Build Specification

_2026-03-23 · Standalone spec for the new implementation_

---

## What This Is

Flux is a multiplayer word-scoring game. Every round all players see the same rack of 8 letters and secretly submit one word. When everyone has submitted, words are revealed simultaneously, scores are updated, and a new rack is spun. Letter point values are **re-randomized every round** — a Z might be worth 1 point, an E might be worth 10. The first player to hit the score target wins the meta-round. Most meta-round wins takes the match.

**Deployment targets**
- API: HuggingFace Spaces (Docker, FastAPI, port 7860)
- Frontend: GitHub Pages (single `index.html`, no build step)

---

## Game Rules

### Setup — Creator Choices

| Setting | Options | Default |
|---------|---------|---------|
| Meta-rounds | 1, 3, 5 | 3 |
| Score target | 100, 200, 500, 1000 | 200 |
| Max players | 2–6 | 2 |

### Core Loop

1. All players see the **same rack of 8 letters**, each with its own point value for this round.
2. Each player secretly submits one word — or passes — before anyone else's choice is revealed.
3. Once every player has submitted, the round **resolves simultaneously**: all words are revealed, scores updated, round summary displayed.
4. If any player's cumulative score has reached the score target, the **meta-round ends**. Otherwise a new rack is spun with new values and the next round begins.

### Word Rules

- 2–20 letters long.
- Spelled using only letters present in the current rack. **Any rack letter may be used more than once in the word** — the rack is treated as a set of available symbols, not a set of one-use tiles. A rack containing one `S` is sufficient to spell `SEASONS`. This is intentional and is what makes the game distinct from Scrabble-style mechanics.
- One **joker tile** (`*`) may be in the rack. It substitutes for exactly one missing letter family (see Joker section).
- Must exist in the dictionary.

### Pass

A player may pass instead of submitting a word. A pass scores 0 points and counts as a valid submission for the round — it does not block round resolution.

### Round Resolution

When the last outstanding submission arrives, the server resolves the round:
1. Scores all submitted words using the current rack's tile values.
2. Adds points to each player's cumulative score.
3. Records the round in history (including the tile values used).
4. Checks whether any player has hit the score target.
   - If yes → end the meta-round (see below).
   - If no → spin a new rack with new tile values, increment `round_num`, clear submissions.

### Meta-Round End

When a player hits the target:
- The player with the highest score wins the meta-round. Tie goes to the player with the lower join index (joined earlier).
- That player's `meta_wins` increments.
- **All players' scores reset to 0.**
- If this was the last meta-round → game moves to `finished`, `meta_round_banner` is not set.
- Otherwise → `meta_round_banner` is set (see shape below); play/pass are blocked until any player calls `/continue`.

**`meta_round_banner` object:**
```json
{
  "winner": "alice",
  "meta_round": 1,
  "next_meta_round": 2,
  "headline": "alice wins Meta-Round 1!",
  "detail": "Continue when you're ready for Meta-Round 2.",
  "continue_label": "Start Meta-Round 2",
  "scores": [
    { "username": "alice", "score": 214, "meta_wins": 1 },
    { "username": "bob",   "score": 187, "meta_wins": 0 }
  ]
}
```

`meta_round_banner` is `null` at all other times.

### Match End

The player with the most meta-round wins is the match winner. Tie goes to the lower join index. The `winner` field is set and the game is read-only (except `/rematch`).

### Lobby

- Players join in `waiting` status.
- Creator can start manually (requires ≥ 2 players).
- If the lobby fills to `max_players`, the game auto-starts.
- Duplicate usernames get a numeric suffix appended automatically.

---

## Scoring

### Per-Rack Tile Values

Every round, before play begins, each letter in the rack is assigned a fresh point value by the Flux Algorithm (see below). These values are visible to all players on the tiles.

### Formula

```
score = base_points − joker_repeat_penalty + length_bonus

base_points          = Σ tile_values[ch] for ch in word
length_bonus         = max(0, len(word) − 7) × 2
joker_repeat_penalty = max(0, word.count(joker_letter) − 1) × tile_values[joker_letter]
```

`tile_values` is the per-rack map for the current round. `joker_letter` is the letter the joker substituted for. The joker repeat penalty uses the substituted letter's tile value — not the joker's own value.

---

## Joker Tile (`*`)

- If `*` is in the rack, a word may use it to cover **one missing letter family**.
- "Missing" means the letter appears in the word but not among the non-joker rack letters.
- The joker covers all occurrences of that letter in the word.
- A word that can be spelled without the joker does not consume it.
- If more than one letter family is missing from the rack, the joker cannot be used (word is invalid).
- The joker tile gets its own value each round from the Flux Algorithm (see Step 4); it can be 0 or a small positive number.

**Example:** Rack is `[A, E, T, R, N, S, O, *]`. Word is "EXTRA". X is not in the rack — the joker covers X. `joker_letter = "X"`. Penalty = `max(0, 1 − 1) × tile_values["X"] = 0`. No penalty because X appears only once.

**Example with penalty:** Same rack, word is "EXCESS". X appears twice, joker covers both. `joker_letter = "X"`. Penalty = `max(0, 2 − 1) × tile_values["X"]`.

---

## Letter Distribution

Letters are drawn without replacement from a weighted bag, so every rack has 8 unique symbols. Weights:

```
A=7  B=2  C=2  D=4  E=9  F=2  G=3  H=2  I=7  J=1  K=1  L=4  M=2
N=6  O=6  P=2  Q=1  R=6  S=4  T=6  U=3  V=2  W=2  X=1  Y=2  Z=1  *=3
```

After drawing, if the rack contains no vowel (A E I O U), one non-vowel non-joker tile is replaced by a vowel drawn from the weighted vowel pool.

---

## Dictionary

- **Primary:** `sowpods.txt` — full tournament word list (~267k words). Load on startup.
- **Fallback:** NLTK `words` corpus, used only if `sowpods.txt` is missing or contains fewer than 50,000 valid entries.
- Filter: alphabetic only, length 2–20, stored uppercase.
- Health endpoint reports active source and dictionary size.

---

## Flux Algorithm

Called once per rack spin, immediately after letters are drawn. Returns a `dict[str, int]` mapping each rack letter (including `*` if present) to a point value for this round.

### Step 1 — Roll a Rack Flavor

```python
flavor = random.choices(
    ["balanced", "spicy", "flat"],
    weights=[55, 30, 15]
)[0]
```

| Flavor | Probability | Character |
|--------|-------------|-----------|
| `balanced` | 55% | Spread across the range; varied mix |
| `spicy` | 30% | One or two breakout-value tiles; rest are low |
| `flat` | 15% | All tiles cluster around 3–5; low variance |

### Step 2 — Build Tier Weights per Flavor

```python
TIER_WEIGHTS = {
    "balanced": {"cheap": 30, "mid": 40, "premium": 22, "rare":  8},
    "spicy":    {"cheap": 45, "mid": 35, "premium": 15, "rare":  5},
    "flat":     {"cheap": 20, "mid": 65, "premium": 15, "rare":  0},
}
TIER_RANGES = {
    "cheap":   (1, 2),
    "mid":     (3, 5),
    "premium": (6, 8),
    "rare":    (9, 10),
}
```

### Step 3 — Assign Initial Values

For each non-joker letter in the rack:

```python
weights = TIER_WEIGHTS[flavor]
tier = random.choices(
    list(weights.keys()),
    weights=list(weights.values())
)[0]
lo, hi = TIER_RANGES[tier]
value = random.randint(lo, hi)
```

### Step 4 — Joker Value (if `*` in rack)

```python
joker_value = random.choices([0, 0, 1, 2, 3, 4, 5], weights=[2,2,1,1,1,1,1])[0]
```

The joker skews low but can occasionally be worth something. Its value does not affect the joker repeat penalty — that uses the substituted letter's tile value.

### Step 5 — Apply Guardrails (in this order)

All guardrails operate only on the **non-joker tile values**. The joker value (set in Step 4) is independent and is never modified by guardrails.

**5a. Minimum spread — ensure at least 2 Cheap tiles**

```python
cheap_indices = [i for i, v in enumerate(values) if v <= 2]
while len(cheap_indices) < 2:
    candidates = sorted(
        [i for i in range(len(values)) if values[i] > 2],
        key=lambda i: values[i]
    )
    i = candidates[0]
    values[i] = random.randint(1, 2)
    cheap_indices = [i for i, v in enumerate(values) if v <= 2]
```

**5b. Maximum concentration — no more than 2 tiles share the same value**

```python
from collections import Counter
for _ in range(20):  # max iterations to prevent infinite loop
    counts = Counter(values)
    crowded = [v for v, c in counts.items() if c > 2]
    if not crowded:
        break
    for val in crowded:
        idxs = [i for i, v in enumerate(values) if v == val]
        for i in idxs[2:]:  # keep first two, adjust the rest
            if values[i] < 10:
                values[i] += 1
            else:
                values[i] -= 1
```

**5c. Sum cap — total of all non-joker values must not exceed 48**

```python
while sum(values) > 48:
    i = values.index(max(values))
    values[i] = max(1, values[i] - 1)
```

**5d. Sum floor — total must be at least 14**

```python
while sum(values) < 14:
    i = values.index(min(values))
    values[i] = min(10, values[i] + 1)
```

### Result

A dict keyed by rack letter. Joker value included if `*` was in the rack.

```python
# Example
{"A": 3, "K": 7, "E": 10, "R": 1, "T": 5, "N": 2, "S": 1, "*": 2}
```

---

## API

**Stack:** FastAPI · Python 3.11 · In-memory state · Sowpods dictionary

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/flux` | none | Create game |
| `POST` | `/flux/{id}/join` | none | Join as player |
| `POST` | `/flux/{id}/start` | creator token | Manually start |
| `GET`  | `/flux/{id}` | none | Poll game state |
| `POST` | `/flux/{id}/play` | player token | Submit a word |
| `POST` | `/flux/{id}/pass` | player token | Pass (0 pts) |
| `POST` | `/flux/{id}/check_word` | player token | Validate word + preview score |
| `POST` | `/flux/{id}/continue` | player token | Advance to next meta-round |
| `POST` | `/flux/{id}/rematch` | player token | Restart with same players/settings |
| `POST` | `/flux/{id}/chat` | player token | Send chat message |
| `GET`  | `/health` | none | Health check |

---

### POST /flux

```json
// Request
{
  "username": "alice",
  "num_meta_rounds": 3,
  "score_target": 200,
  "max_players": 2
}

// Response
{ "game_id": "A1B2C3D4", "player_token": "<uuid>" }
```

### POST /flux/{id}/join

```json
// Request
{ "username": "bob" }

// Response
{ "game_id": "A1B2C3D4", "player_token": "<uuid>", "username": "bob" }
```

### POST /flux/{id}/start

```json
// Request
{ "player_token": "<uuid>" }

// Response: full game state (see GET below)
```

Creator only (index 0). Requires ≥ 2 players in lobby.

### GET /flux/{id}

```json
{
  "game_id": "A1B2C3D4",
  "status": "waiting | playing | finished",
  "num_meta_rounds": 3,
  "meta_round": 1,
  "round_num": 4,
  "score_target": 200,
  "max_players": 2,
  "players": [
    {
      "username": "alice",
      "score": 47,
      "meta_wins": 1,
      "history": [
        {
          "meta_round": 1,
          "round": 1,
          "word": "QUEST",
          "letters": ["Q","U","E","S","T","A","N","H"],
          "tile_values": {"Q":9,"U":1,"E":3,"S":2,"T":5,"A":1,"N":4,"H":7},
          "points": 25,
          "base_points": 25,
          "length_bonus": 0,
          "joker_letter": null,
          "joker_repeat_penalty": 0
        }
      ]
    }
  ],
  "current_letters": ["A","K","E","R","T","N","S","*"],
  "tile_values": {"A":3,"K":7,"E":10,"R":1,"T":5,"N":2,"S":1,"*":2},
  "submitted_players": ["alice"],
  "meta_round_banner": null,
  "winner": null,
  "log": ["...last 20 events..."],
  "chat": ["...last 40 messages..."],
  "last_round_summary": {
    "meta_round": 1,
    "round": 3,
    "letters": ["Q","U","E","S","T","A","N","H"],
    "tile_values": {"Q":9,"U":1,"E":3,"S":2,"T":5,"A":1,"N":4,"H":7},
    "headline": "Best round: alice with QUEST for 25 pts",
    "detail": "Board: Q U E S T A N H",
    "best_points": 25,
    "best_players": ["alice"],
    "best_words": ["QUEST"],
    "tone": "green | yellow | red"
  },
  "round_history": [
    {
      "meta_round": 1,
      "round": 1,
      "letters": ["..."],
      "tile_values": {"..."},
      "headline": "...",
      "detail": "...",
      "best_points": 25,
      "best_players": ["alice"],
      "best_words": ["QUEST"],
      "tone": "green",
      "results": [
        {
          "username": "alice",
          "word": "QUEST",
          "points": 25,
          "base_points": 25,
          "length_bonus": 0,
          "joker_letter": null,
          "joker_repeat_penalty": 0
        }
      ]
    }
  ]
}
```

**Notes:**
- `tile_values` is the per-rack point map for the current round. Also stored per entry in `round_history` so historical scoring is reviewable.
- `submitted_players` lists usernames who have submitted this round — **not what they submitted**. Words stay hidden until all players submit.
- `last_round_summary` tone is a **heat indicator** for how exciting the round was, not a quality judgment: `"green"` = low-scoring/quiet round, `"yellow"` = good round (best word ≥ 21 pts), `"red"` = hot round (best word ≥ 31 pts). Think of it as a temperature scale — red is the best outcome, not a warning.
- `log` is an array of plain strings, each a human-readable event (emoji-prefixed). Examples: `"🤫 alice submitted"`, `"🎯 alice wins Meta-Round 1!"`, `"➡️ Round 4 — new letters!"`. Render as a simple list; no parsing needed.
- `log` returns the last 20 events; `chat` returns the last 40 messages.

### POST /flux/{id}/play

```json
// Request
{ "player_token": "<uuid>", "word": "quest" }

// Response: full game state
```

Errors: 400 if word can't be formed from rack, not in dictionary, already submitted, or meta-round banner is active. 403 if invalid token.

### POST /flux/{id}/pass

```json
// Request
{ "player_token": "<uuid>" }

// Response: full game state
```

### POST /flux/{id}/check_word

```json
// Request
{ "player_token": "<uuid>", "word": "quest" }

// Response
{
  "word": "QUEST",
  "in_dictionary": true,
  "points": 25
}
```

Does not advance game state. Used for live UI feedback. Returns `points: 0` if word is not in dictionary or can't be formed from the current rack.

### POST /flux/{id}/continue

```json
// Request
{ "player_token": "<uuid>" }

// Response: full game state
```

Any player may call this. Clears `meta_round_banner`, increments `meta_round`, resets scores, spins new rack with new tile values.

### POST /flux/{id}/rematch

```json
// Request
{ "player_token": "<uuid>" }

// Response: full game state
```

Only valid when `status` is `"finished"`. Resets all scores, `meta_wins`, and history. Keeps same players and settings. The game moves directly back to `playing` (new rack spun immediately) — it does not return to `waiting`. The frontend should skip the lobby screen and go straight to the game screen.

### POST /flux/{id}/chat

```json
// Request
{ "player_token": "<uuid>", "message": "nice word!" }

// Response
{ "ok": true }
```

Message capped at 200 characters. Returned in game state as `chat` array items: `{ "username": "alice", "text": "nice word!" }`.

### GET /health

```json
{
  "status": "ok",
  "active_games": 4,
  "dictionary_size": 267751,
  "dictionary_source": "sowpods | nltk"
}
```

---

### Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request — invalid settings, word invalid, already submitted, wrong game state |
| 403 | Wrong token or insufficient permissions (only creator can start) |
| 404 | Game not found |

---

## State Machine

```
waiting ──(start or lobby fills, ≥2 players)──► playing
                                                   │
                                          round resolves
                                                   │
                                    ┌──────────────┴──────────────┐
                              target hit?                     no target
                                   │                              │
                           meta_round_banner               next round
                                   │                         (new rack)
                            /continue called
                                   │
                    ┌──────────────┴──────────────┐
               more meta-rounds?             last meta-round
                    │                              │
               next meta-round               finished ──(/rematch)──► playing
```

- **`waiting`**: players join; game has not started
- **`playing`**: active game; play/pass accepted; play/pass blocked when `meta_round_banner` is set
- **`finished`**: read-only except `/rematch`

---

## Infrastructure

| Component | Notes |
|-----------|-------|
| API | HuggingFace Spaces, Docker SDK, port 7860, Python 3.11 |
| Frontend | GitHub Pages, single `index.html`, no build step |

- State is **in-memory** — restart clears all games
- Games auto-expire after **4 hours** (cleaned up lazily on next `/flux` create call)
- CORS: allow all origins
- No auth, no database, no accounts

---

## Frontend

### Stack

Single `index.html` — all HTML, CSS, and JS in one file. No framework, no build step, no dependencies. Served from GitHub Pages.

### Screens

**Setup** → **Lobby** → **Game** → **Game Over**

URL param `?game=GAMEID` pre-fills a join link for sharing.

### State Persistence

`localStorage` stores `gameId` + `playerToken` — survives tab close, browser restart, and accidental navigation away. Last-used username and game settings also stored in `localStorage`.

On page load, if `localStorage` contains a `gameId` and `playerToken`, the frontend immediately polls that game and resumes where the player left off — no setup screen shown.

**"Forget this game"** is an explicit UI action (small link or secondary button, not the primary CTA) that clears `gameId` and `playerToken` from `localStorage` and returns the player to the setup screen. This is the only way to intentionally abandon a game. There is no "Leave" button.

### Polling

Poll `GET /flux/{id}` every 1500 ms during active game.

### Game Screen Layout

- **Main area:** rack display, word input, scoreboard
- **Right rail (permanent):** chat panel + past board history (always visible, not a modal)

### Rack Display

- 8 letter tiles in a row
- Each tile shows its current point value, color-coded:
  - Grey: 1–2 pts
  - White: 3–5 pts
  - Yellow: 6–8 pts
  - Orange/red: 9–10 pts
- Joker tile shows `★N` where N is its current value
- On new rack: slot-reel `spin-in` animation, then values fade in

### Word Input

- Letters highlight as player types (shows which rack letters are being used)
- Real-time point preview updates on each keystroke (calls `/check_word`)
- Submit button locks in the word; player sees a "waiting for others" state
- Submitted players shown by username (not their word)

### Round Reveal

- All words shown simultaneously when round resolves
- Best-word summary banner with tone color (green / yellow / red)
- Past-board panel in right rail shows `tile_values` for each historical round

### Meta-Round Banner

- Full-screen (or prominent overlay) between meta-rounds
- Shows meta-win counts per player
- "Continue" button (any player can press) calls `/continue`

### Scoreboard

- One row per player: name, current score, progress bar toward target, meta-win count, last 5 words as chips

### Setup Screen

- Meta-rounds selector, score target selector, max players selector
- Username field (pre-filled from localStorage)

### Chat Panel

- Visible during lobby and game (right rail)
- Messages from all players; sent via `/chat`

---

## Open Questions (tune after play-testing)

1. **Rack sum range** — cap currently 48. Adjust once typical round scores are observed.
2. **Flavor probabilities** — 30% spicy may feel frequent; 15% flat may feel slow. Tune after a few sessions.
3. **Joker repeat penalty** — currently uses the substituted letter's tile value. Confirm this feels correct vs. using the joker's own value or dropping the penalty entirely.
4. **Length bonus** — a high-value spicy rack + 8-letter word could score very high. May want to cap or reduce the length bonus.
5. **Per-round vs. per-meta-round re-roll** — if new values every round feels like too much to absorb, consider re-rolling only once per meta-round.
6. **Show rack flavor?** — displaying "SPICY" as a label could be fun or could anchor expectations. Try both.
