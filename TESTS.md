# Tests Base Spec

This document defines the default testing approach for lightweight board-based games with a frontend, a backend API, and game-state logic. It is intended to be copied into similar projects and used as a reusable base.

## How To Use This Spec

Use this document as the shared testing base for any game project that has:

- backend game logic
- backend API routes
- frontend interaction logic
- a local development workflow

This spec is meant to work alongside:

- `GAMES.md` for board, lifecycle, identity, and rejoin behavior
- a game-specific rules spec for the actual gameplay mechanics

Recommended split:

- `TESTS.md` defines how the project should be tested
- the game-specific rules spec defines what the game should do

`TESTS.md` should usually own:

- test categories
- test boundaries
- local-vs-deployed testing strategy
- default test commands
- minimum expected coverage areas

The game-specific rules doc should usually own:

- the exact scenarios that must be true for that game
- scoring expectations
- win-condition expectations
- rule-specific examples that should become tests

## Testing Philosophy

Default priority:

1. local tests should be the main source of truth
2. deployed checks should be smoke tests, not the main test suite
3. backend logic should be tested separately from backend route wiring
4. frontend logic should be tested separately from visual styling

Goals:

- fast feedback while building
- deterministic coverage for important game rules
- clear separation between pure logic failures and integration failures
- minimal dependence on external deployment state

## Default Test Layers

Projects should usually have these layers:

### 1. Backend Logic Tests

Purpose:

- verify pure game logic without HTTP or browser concerns

Examples:

- validation rules
- score calculations
- round resolution
- state transitions
- leave/rejoin behavior
- winner determination
- edge cases around inactivity or abandonment

Recommended properties:

- fast
- deterministic
- no network
- no server process required

### 2. Backend API Tests

Purpose:

- verify route behavior and request/response contracts locally

Examples:

- create game
- list games
- join game
- rejoin game
- leave game
- play/pass/check endpoints
- invalid token behavior
- missing game behavior

Recommended implementation:

- local framework test client
- for FastAPI projects, prefer `fastapi.testclient.TestClient`

Recommended properties:

- no external deployment dependency
- assert status codes and payload shape
- use seeded or controlled state where possible

### 3. Frontend Logic Tests

Purpose:

- verify UI decision logic without requiring full browser automation

Examples:

- result messaging
- join/rejoin button behavior logic
- move-to-another-device formatting helpers
- tile highlighting helpers
- game-board card state rendering helpers

Recommended implementation:

- extract testable frontend logic into small JS modules
- avoid testing large inline HTML scripts directly when possible

Recommended properties:

- fast
- deterministic
- independent of visual design details

### 4. Optional Browser Or End-To-End Tests

Purpose:

- verify a few critical user flows in a real browser when the project grows enough to justify it

Examples:

- create game in one browser and see it in another
- join from board
- leave and rejoin
- move to another device

These are optional by default. Do not require them before basic local unit/API coverage exists.

## Local First, Deployment Second

Default rule:

- use local tests for real verification
- use deployed environments only for smoke checks

Why:

- local tests are faster
- local tests are more deterministic
- deployment/network issues should not block most test runs

Recommended deployment smoke checks:

- health endpoint responds
- latest deploy is reachable
- one or two basic route checks

Do not use the deployed environment as the primary substitute for unit tests or local API tests.

## Minimum Coverage Areas

Any similar game project should aim to cover:

### Backend Logic

- valid moves or submissions
- invalid moves or submissions
- state transitions across rounds
- leave behavior
- rejoin behavior
- all-players-left behavior
- end-of-game behavior

### Backend API

- create
- list
- join
- rejoin
- leave
- at least one core gameplay endpoint
- invalid token handling
- not-found handling

### Frontend Logic

- message rendering for success and failure states
- join/rejoin decision logic
- board empty state behavior
- transfer/rejoin helper logic if cross-device flow exists

## Identity And Rejoin Testing

If the game supports rejoin or device transfer, tests should explicitly cover:

- leaving a game
- rejoining the same unfinished game
- restoring the same player identity
- not creating duplicate players
- rotating or replacing the active session token when using cross-device rejoin
- invalid rejoin code behavior

If the product includes `Move to another device`, tests should verify:

- the player can reconnect on a second device
- the original identity is preserved
- the transfer does not create a second participant record

## Board-Level Testing

If the default opening screen is a live game board, tests should cover:

- empty state when no games exist
- list population when games exist
- board state labels
- join/rejoin button availability
- refresh behavior if board polling is implemented

## UI Testing Boundaries

Do not over-test purely cosmetic details in unit tests.

Good unit test targets:

- text selection logic
- state-to-message mapping
- helper functions
- API payload interpretation

Poor unit test targets by default:

- exact spacing
- exact colors
- exact animation timing

Visual design should usually be checked manually unless the project later adopts screenshot testing.

## Recommended File Layout

Default structure:

- `tests/test_game_logic.py`
- `tests/test_api.py`
- `tests/frontend_logic.test.js`
- optional small frontend helper modules extracted from HTML or inline scripts
- a single local runner script such as `run_tests.sh`

If the stack differs, keep the same separation even if the filenames change.

## Recommended Commands

Projects should expose one simple local test command.

Recommended default:

```bash
bash run_tests.sh
```

That script should run:

- backend logic tests
- backend API tests
- frontend logic tests

## Environment Expectations

Tests should assume:

- local virtualenv or local dependency environment exists
- test runs should not require production credentials
- test runs should not require deployed services

If API test dependencies are not available in a given environment, tests may skip gracefully, but the preferred project setup is to make the full local suite runnable.

## Notes

- Favor many small deterministic tests over a few fragile all-in-one tests.
- When a bug is found in manual testing, add a test that would have caught it.
- Local tests should be easy enough to run before every push.
- Browser or deployed smoke checks are useful, but they should not replace local automated coverage.
