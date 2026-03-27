# Bot Opponent Pattern

This document sketches a reusable pattern for adding a bot opponent to casual multiplayer games, especially board-first web games with a lightweight API and no account system.

It is written to be game-agnostic so other projects can reuse it.

## Goal

Support a `You vs Bot` mode that:

- feels instant to create
- works from the normal board / lobby flow
- does not require a second human
- can be implemented without a real-time AI system
- can be tuned anywhere from "fair opponent" to "comedy monster"

## Product Shape

The cleanest user-facing model is:

- normal multiplayer remains unchanged
- create flow adds a `vs bot` or `solo vs bot` option
- the bot appears as a normal participant in the game state
- the server controls all bot actions

The bot should not be a frontend illusion. It should be represented in server state so:

- round resolution stays authoritative
- reconnects are consistent
- history and summaries stay accurate
- other clients see the same results

## Recommended Bot Modes

### 1. Fair Bot

The bot plays plausible but not perfect moves.

Good for:

- tutorial play
- onboarding
- low-friction solo practice

Behavior:

- valid but not always optimal
- slight randomness
- occasional mistakes or passes

### 2. Strong Bot

The bot often finds one of the best moves available.

Good for:

- challenge mode
- "practice against a beast"

Behavior:

- searches valid moves
- heavily score-driven
- consistent pressure

### 3. Comedy Bot

The bot is intentionally rude, absurdly strong, or theatrically overpowered.

Good for:

- joke modes
- alpha experiments
- personality-driven games

Behavior:

- suspiciously perfect move selection
- playful taunts or summary copy
- can "dwarf the meat computer" on purpose

This mode is especially useful when the bot itself is part of the joke.

## Core Architecture

### Server-owned bot

Recommended default:

- the bot is stored as a normal player-like participant
- mark it with `is_bot: true`
- optionally include `bot_profile`, `bot_mode`, or `bot_difficulty`

Example shape:

```json
{
  "player_id": "bot-1",
  "username": "MEATGRINDER-7",
  "active": true,
  "is_bot": true,
  "bot_mode": "comedy"
}
```

### Trigger model

Bots should act on server-side triggers rather than timers whenever possible.

Recommended:

- when a round begins, bot move can be precomputed
- when all human-required inputs are in, server resolves including bot submission
- if the game needs pacing, add a short fake thinking delay in the frontend rather than a real backend scheduler

This keeps implementation simple and avoids background job complexity.

## Decision Strategies

### Strategy A: Rule-based picker

Server generates a list of legal moves and chooses one according to weighted rules.

Example heuristics:

- highest score
- top 10% random pick
- prefer longer words
- prefer funny or dramatic words
- sometimes intentionally underplay

Best when:

- game rules are deterministic
- legal move generation is already possible

### Strategy B: Precomputed search

Server searches the dictionary or move space for all legal options for the current board.

Then:

- sort by score
- apply mode bias
- choose a move

Best when:

- move generation is not too expensive
- game state is compact

### Strategy C: Fabricated comedy profile

The bot is tuned for entertainment, not fairness.

Examples:

- always finds a near-perfect move
- uses special summary text
- occasionally "miraculously" finds an outrageous word

Important note:

If using this mode, decide whether the bot is:

- honestly legal but very strong
- softly cheating

For most games, "honestly legal but theatrically strong" is the sweet spot.

## UX Recommendations

### Create flow

Recommended options:

- `Solo`
- `Solo vs Bot`
- normal multiplayer sizes

If the game already supports solo, `Solo vs Bot` should be visually distinct from plain solo.

### Board

Board rows should show bot games clearly.

Examples:

- `solo vs bot`
- `1 human + bot`
- `bot match`

### In-game

The bot should be visually obvious:

- badge the bot in scoreboard / player list
- use a distinct name
- optionally add a tiny bot icon

### Match summaries

This is where bot personality pays off.

Examples:

- `MEATGRINDER-7 produced another alarmingly efficient answer.`
- `Board Intelligence has, regrettably, seen all possible futures.`
- `The bot remains deeply unimpressed by biology.`

## Difficulty Tuning

Good difficulty knobs:

- probability of choosing top-scoring move
- randomness among top candidates
- chance to pass
- chance to choose style over score
- delay before reveal

Comedy knobs:

- how often it finds a "perfect" move
- how smug the copy is
- whether it reacts to player performance

## Data Model

Recommended fields:

```json
{
  "is_bot": true,
  "bot_mode": "fair | strong | comedy",
  "bot_profile": "default",
  "bot_difficulty": 0.85
}
```

Optional game-level fields:

```json
{
  "has_bot": true,
  "bot_count": 1
}
```

## API Guidance

Usually no new endpoints are required.

Preferred pattern:

- create game request includes bot option
- server inserts bot participant during game creation
- normal game state endpoint returns bot as part of players
- normal play/resolve flow includes bot action automatically

This keeps the bot inside the game rules rather than bolted on beside them.

## Testing Guidance

Must-cover tests:

- create bot game
- bot appears in game state
- bot does not require a human token
- bot submits when expected
- round resolves correctly with bot included
- reconnect / refresh still shows bot consistently
- end-of-match summaries and scores include bot correctly

For comedy or strong bots:

- bot move is legal
- bot score is explainable under game rules
- difficulty knobs actually affect choice

## Anti-patterns

Avoid:

- frontend-only fake bot moves
- hidden server cheats without deciding that intentionally
- real background schedulers when round-trigger logic is enough
- bot code mixed directly into UI rendering logic

## Implementation Advice

For most games, build in this order:

1. Add `is_bot` support to player/game state.
2. Add create-flow support for a bot match.
3. Make the server auto-submit a legal bot move.
4. Render bot identity clearly in the UI.
5. Add personality and polish only after the core loop works.

## Flux-specific Direction

If implemented in Flux, the funniest first version is probably:

- `Solo vs Bot` as a create option
- one server-owned bot player
- comedy-strength move selection
- dramatic post-round copy

That would be much easier than a fully "smart" bot system and probably much more memorable.
