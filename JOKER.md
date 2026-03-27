# Joker Rules In Flux

This document describes how the `*` joker works in the current Flux implementation.

## Short Version

- A rack may contain one joker tile: `*`.
- The joker can stand in for exactly one missing letter family.
- The first use of that missing letter scores at the joker tile's value.
- Every additional use of that same missing letter family scores `0`.
- The joker does not help if the word is missing two or more different letter families.

## Validation

A word is valid with a joker when:

- the word is otherwise in the dictionary
- all needed letters are already in the rack except one missing letter family
- the rack contains `*`

If the word is missing more than one distinct letter family, the word is invalid.

## Scoring Rule

Flux uses:

```text
score = base_points - joker_repeat_penalty + length_bonus
```

Where:

- `base_points` adds the joker tile's value for every occurrence of the substituted letter
- `joker_repeat_penalty` subtracts that joker value back out for every occurrence after the first
- `length_bonus = max(0, len(word) - 7) * 2`

That means the net effect is:

- first joker-covered letter: scores the joker value
- second and later copies of that same letter: score `0`

## Examples

If the rack is:

```text
A R T S I *    and the joker is worth 7
```

Word: `BARS`

- `B` is the only missing letter family
- the joker stands in for `B`
- score contribution from `B` = `7`
- `A`, `R`, `S` score from their own tile values

Word: `BBBBARS`

- all `B`s are covered by the same joker letter family
- base scoring counts all four `B`s at `7` each
- repeat penalty subtracts three of those back out
- net `B` contribution is still just `7`

Word: `ZIZZ`

- if `Z` is the joker-covered letter and `* = 7`
- the first `Z` contributes `7`
- the other `Z`s contribute `0`
- `I` contributes its normal tile value

## Important Consequence

The joker is not a repeated high-value multiplier.

Even if the joker is worth a lot this round, words like `ZIZZ` or `BBBBARS` only get the joker's value once total for the substituted letter family.

## Current Code Reference

The behavior is implemented in:

- [game.py](/Users/pleddy/docs/cloudautomat/code/projects/flux/game.py)

The main logic lives in:

- `analyze_word(...)` for validation
- `score_word(...)` for scoring
