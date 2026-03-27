# Games Base Spec

This document defines the default lifecycle, board behavior, and join/leave rules for games in the overall game board. It is intended to be a reusable base for future games, not just Flux.

## Overview

The system supports a list of games. Each game is a joinable activity with:

- a creator
- zero or more currently active players
- zero or more inactive former players who may be allowed to rejoin while unfinished
- a visible state on the game board
- a lifecycle that ends in a finished state

The default product pattern is:

1. Users land on a game board first.
2. The board shows current games, or an empty state if there are none.
3. Users can create a game from that board.
4. Users can join or rejoin existing unfinished games directly from that board.

## Core Rules

1. There is a visible list of games.
2. The list is the default opening screen.
3. The board should still render when there are no games, using an explicit empty state.
4. Players can join unfinished games.
5. Players can leave unfinished games at any time.
6. Players who leave an unfinished game can rejoin that same game.
7. Games become `finished` when either:
   - the game completes normally, or
   - all players leave
8. The current state of every game must be visible on the board.
9. Solo games and multiplayer games are both valid.

## Default Board UX

The board should include:

- a `Create Game` action
- a manual `Join By Code` action
- a list of current games
- a clear empty state when there are no games

Each board row or card should show at least:

- game identifier or title
- creator
- state
- player count
- round progress or equivalent progress
- a `Join` or `Rejoin` action when allowed

The board should live-refresh while open. Polling is acceptable as a default implementation.

## Suggested Board States

At minimum, each game should expose one clear board-level state:

- `waiting`
- `active`
- `finished`

Optional finer-grained states:

- `in_round`
- `between_rounds`
- `abandoned`

The important requirement is that the game board always communicates current state clearly.

## Joining, Leaving, And Rejoining

Each game should track:

- the creator
- all players who have ever joined
- which players are currently active

Rules:

- Players may join an unfinished game.
- Players may leave at any time.
- A player who leaves an unfinished game may later rejoin it.
- Rejoin should restore that player’s existing slot when possible, rather than creating a duplicate participant.
- If all players leave, the game should be marked `finished`.

## Identity And Rejoin UX

Default UX behavior:

- If the system already knows the user’s name, joining from the board should be one click.
- If the user just left a game, that game’s board action should become `Rejoin`.
- Clicking `Rejoin` should attempt to rejoin directly, without routing the user through a form.
- If the board knows a likely username from local memory or recent session state, it may use that to join directly.
- Only fall back to a join form when the system does not know who the player is.

Default remembered values:

- last known username
- last unfinished game the player left

## Active Vs Inactive Players

Games should distinguish between:

- active players
- inactive players who previously joined

Board counts and in-game participant displays should generally use active players.

Inactive players should:

- not block round resolution
- not appear as current participants unless explicitly labeled
- be eligible for rejoin while the game is unfinished

## Creator Authority

The creator is the default authority for creator-only controls.

Creator-only actions may include:

- starting the game
- advancing rounds
- final completion actions

Non-creator players may:

- join unfinished games
- leave at any time
- rejoin unfinished games they were already part of
- participate in gameplay

Non-creator players may not perform creator-only control actions unless a specific game explicitly changes that rule.

## Completion Rules

A game becomes `finished` when:

- the final round or final game condition is completed, or
- every player has left

Once finished:

- the board should reflect the finished state
- direct joining and rejoining should stop unless the product defines a restart or clone flow
- the game should no longer accept progression actions

## Recommended API Shape

At minimum, the system should support:

- list games
- create game
- join game
- leave game
- get game state

Recommended board list response fields:

- `game_id`
- `creator`
- `state`
- `active_players`
- `max_players`
- round or progress summary
- `can_join`

Recommended game-level player fields:

- stable player identity
- active/inactive status
- creator marker or creator identity

## Minimal Data Model

A minimal game record could include:

- `game_id`
- `title`
- `creator_id`
- `state`
- `mode`
  - `solo`
  - `multiplayer`
- `round_index`
- `round_count`
- `player_ids`
- `active_player_ids`
- `finished_at`

A minimal player record could include:

- `player_id`
- `display_name`
- `active`
- `joined_at`
- `left_at`

## Frontend Behavior Defaults

Default frontend behavior should be:

- show the board on first load
- auto-refresh the board while the user remains on it
- stop board polling once the user enters a game or lobby
- resume board polling when the user returns home
- if the user leaves a game, return them to the board immediately
- reset the viewport to the top when returning to the board

## Notes

- “All players leave” should be treated as a terminal completion rule by default, not a temporary empty room.
- Rejoining is allowed only while the game is still unfinished.
- Direct board join/rejoin is the preferred default experience.
- The join form should be a fallback, not the primary path, when the system already knows the player identity.
- Solo games should follow the same lifecycle rules, with the creator also being the only participant.
