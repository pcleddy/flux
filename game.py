"""
Flux — core game logic, state machine, and Flux Algorithm.
"""

from __future__ import annotations

import random
import string
import time
import uuid
from collections import Counter
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LETTER_WEIGHTS = {
    "A": 7,  "B": 2,  "C": 2,  "D": 4,  "E": 9,  "F": 2,  "G": 3,
    "H": 2,  "I": 7,  "J": 1,  "K": 1,  "L": 4,  "M": 2,  "N": 6,
    "O": 6,  "P": 2,  "Q": 1,  "R": 6,  "S": 4,  "T": 6,  "U": 3,
    "V": 2,  "W": 2,  "X": 1,  "Y": 2,  "Z": 1,  "*": 3,
}

VOWELS = set("AEIOU")
NON_VOWEL_LETTERS = [l for l in LETTER_WEIGHTS if l not in VOWELS and l != "*"]

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

GAME_TTL = 4 * 3600  # 4 hours in seconds

# ---------------------------------------------------------------------------
# Dictionary (loaded once, injected at startup)
# ---------------------------------------------------------------------------

_dictionary: set[str] = set()
_dictionary_source: str = "none"


def set_dictionary(words: set[str], source: str) -> None:
    global _dictionary, _dictionary_source
    _dictionary = words
    _dictionary_source = source


def get_dictionary_info() -> tuple[int, str]:
    return len(_dictionary), _dictionary_source


def in_dictionary(word: str) -> bool:
    return word.upper() in _dictionary


# ---------------------------------------------------------------------------
# Flux Algorithm
# ---------------------------------------------------------------------------

def flux_algorithm(rack: list[str]) -> dict[str, int]:
    """
    Given the 8 rack letters (including '*' if present), return a dict mapping
    each letter to its point value for this round.
    """
    non_joker = [l for l in rack if l != "*"]
    has_joker = "*" in rack

    # Step 1 — Roll flavor
    flavor = random.choices(
        ["balanced", "spicy", "flat"],
        weights=[55, 30, 15],
    )[0]

    # Step 2/3 — Assign initial values for non-joker tiles
    weights = TIER_WEIGHTS[flavor]
    values = []
    for _ in non_joker:
        tier = random.choices(
            list(weights.keys()),
            weights=list(weights.values()),
        )[0]
        lo, hi = TIER_RANGES[tier]
        values.append(random.randint(lo, hi))

    # Step 4 — Joker value
    joker_value: Optional[int] = None
    if has_joker:
        joker_value = random.choices(
            [0, 0, 1, 2, 3, 4, 5],
            weights=[2, 2, 1, 1, 1, 1, 1],
        )[0]

    # Step 5 — Guardrails (non-joker tiles only)

    # 5a. Minimum spread — at least 2 cheap tiles (value <= 2)
    cheap_indices = [i for i, v in enumerate(values) if v <= 2]
    while len(cheap_indices) < 2:
        candidates = sorted(
            [i for i in range(len(values)) if values[i] > 2],
            key=lambda i: values[i],
        )
        i = candidates[0]
        values[i] = random.randint(1, 2)
        cheap_indices = [i for i, v in enumerate(values) if v <= 2]

    # 5b. Maximum concentration — no more than 2 tiles share the same value
    for _ in range(20):
        counts = Counter(values)
        crowded = [v for v, c in counts.items() if c > 2]
        if not crowded:
            break
        for val in crowded:
            idxs = [i for i, v in enumerate(values) if v == val]
            for i in idxs[2:]:
                if values[i] < 10:
                    values[i] += 1
                else:
                    values[i] -= 1

    # 5c. Sum cap — total must not exceed 48
    while sum(values) > 48:
        i = values.index(max(values))
        values[i] = max(1, values[i] - 1)

    # 5d. Sum floor — total must be at least 14
    while sum(values) < 14:
        i = values.index(min(values))
        values[i] = min(10, values[i] + 1)

    # Build result dict
    result: dict[str, int] = {}
    for letter, val in zip(non_joker, values):
        result[letter] = val
    if has_joker and joker_value is not None:
        result["*"] = joker_value

    return result


# ---------------------------------------------------------------------------
# Rack generation
# ---------------------------------------------------------------------------

def draw_rack() -> list[str]:
    """Draw 8 unique symbols from the weighted bag; guarantee ≥1 vowel."""
    population = list(LETTER_WEIGHTS.keys())
    weights = list(LETTER_WEIGHTS.values())

    chosen: list[str] = []
    remaining_pop = population.copy()
    remaining_w = weights.copy()

    while len(chosen) < 8:
        idx = random.choices(range(len(remaining_pop)), weights=remaining_w)[0]
        letter = remaining_pop[idx]
        chosen.append(letter)
        # Remove from pool (draw without replacement — each symbol unique)
        remaining_pop.pop(idx)
        remaining_w.pop(idx)

    # Ensure at least one vowel
    has_vowel = any(l in VOWELS for l in chosen)
    if not has_vowel:
        # Replace one non-vowel non-joker tile with a vowel from the vowel pool
        non_vowel_idxs = [i for i, l in enumerate(chosen) if l not in VOWELS and l != "*"]
        replace_idx = random.choice(non_vowel_idxs)
        # Weighted vowel pool (only vowels not already in the rack)
        available_vowels = [v for v in VOWELS if v not in chosen]
        if available_vowels:
            vowel_weights = [LETTER_WEIGHTS[v] for v in available_vowels]
            new_vowel = random.choices(available_vowels, weights=vowel_weights)[0]
            chosen[replace_idx] = new_vowel

    return chosen


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_word(word: str, tile_values: dict[str, int], joker_letter: Optional[str]) -> dict:
    """
    Returns a dict with: points, base_points, length_bonus, joker_letter, joker_repeat_penalty.
    word must be uppercase.
    """
    word = word.upper()
    base_points = sum(tile_values.get(ch, 0) for ch in word)
    length_bonus = max(0, len(word) - 7) * 2

    joker_repeat_penalty = 0
    if joker_letter:
        count = word.count(joker_letter)
        joker_repeat_penalty = max(0, count - 1) * tile_values.get(joker_letter, 0)

    points = base_points - joker_repeat_penalty + length_bonus

    return {
        "points": points,
        "base_points": base_points,
        "length_bonus": length_bonus,
        "joker_letter": joker_letter,
        "joker_repeat_penalty": joker_repeat_penalty,
    }


# ---------------------------------------------------------------------------
# Word validation
# ---------------------------------------------------------------------------

def analyze_word(word: str, rack: list[str], tile_values: dict[str, int]) -> dict:
    """
    Returns a structured validation result for a candidate word.
    Rack letters use set semantics, not one-use tile semantics.
    """
    word = word.upper()

    if len(word) < 2 or len(word) > 20:
        return {
            "ok": False,
            "code": "invalid_format",
            "message": "Word must be 2–20 letters long.",
            "joker_letter": None,
        }

    if not word.isalpha():
        return {
            "ok": False,
            "code": "invalid_format",
            "message": "Word must contain only letters.",
            "joker_letter": None,
        }

    if not in_dictionary(word):
        return {
            "ok": False,
            "code": "not_in_dictionary",
            "message": "Not a word.",
            "joker_letter": None,
        }

    rack_set = set(rack)
    non_joker_set = rack_set - {"*"}
    has_joker = "*" in rack_set

    # Find which letter families are missing from the non-joker rack
    missing_families = {ch for ch in word if ch not in non_joker_set}

    if len(missing_families) == 0:
        joker_letter = None
    elif len(missing_families) == 1 and has_joker:
        joker_letter = next(iter(missing_families))
    else:
        return {
            "ok": False,
            "code": "missing_letters",
            "message": "You don't have the letters.",
            "joker_letter": None,
        }

    return {
        "ok": True,
        "code": "valid",
        "message": "Good word.",
        "joker_letter": joker_letter,
    }


def validate_word(word: str, rack: list[str], tile_values: dict[str, int]) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Returns (is_valid, joker_letter_or_none, error_message_or_none).
    """
    analysis = analyze_word(word, rack, tile_values)
    return analysis["ok"], analysis["joker_letter"], None if analysis["ok"] else analysis["message"]


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

class PlayerState:
    def __init__(self, username: str, token: str, join_index: int):
        self.username = username
        self.token = token
        self.join_index = join_index
        self.active: bool = True
        self.score: int = 0
        self.meta_wins: int = 0
        self.history: list[dict] = []
        self.current_submission: Optional[dict] = None  # {"word": ..., "joker_letter": ..., ...} or {"pass": True}

    def to_dict(self, include_submission=False) -> dict:
        d = {
            "username": self.username,
            "join_index": self.join_index,
            "active": self.active,
            "score": self.score,
            "meta_wins": self.meta_wins,
            "history": self.history,
        }
        if include_submission:
            d["submission"] = self.current_submission
        return d


class FluxGame:
    def __init__(
        self,
        game_id: str,
        creator_token: str,
        username: str,
        num_meta_rounds: int,
        score_target: int,
        max_players: int,
    ):
        self.game_id = game_id
        self.num_meta_rounds = num_meta_rounds
        self.score_target = score_target
        self.max_players = max_players
        self.status: str = "waiting"
        self.meta_round: int = 1
        self.round_num: int = 0
        self.created_at: float = time.time()

        self.players: list[PlayerState] = []
        self.token_map: dict[str, int] = {}  # token -> join_index

        self.current_letters: list[str] = []
        self.tile_values: dict[str, int] = {}

        self.log: list[str] = []
        self.chat: list[dict] = []
        self.round_history: list[dict] = []
        self.last_round_summary: Optional[dict] = None
        self.meta_round_banner: Optional[dict] = None
        self.winner: Optional[str] = None

        # Add creator as first player
        p = PlayerState(username, creator_token, 0)
        self.players.append(p)
        self.token_map[creator_token] = 0
        self._log(f"🎮 {username} created the game.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        self.log.append(msg)
        if len(self.log) > 20:
            self.log = self.log[-20:]

    def _get_player_by_token(self, token: str) -> Optional[PlayerState]:
        idx = self.token_map.get(token)
        if idx is None:
            return None
        return self.players[idx]

    def _active_players(self) -> list[PlayerState]:
        return [p for p in self.players if p.active]

    def _submitted_count(self) -> int:
        return sum(1 for p in self._active_players() if p.current_submission is not None)

    def _spin_rack(self) -> None:
        self.current_letters = draw_rack()
        self.tile_values = flux_algorithm(self.current_letters)
        self.round_num += 1
        for p in self.players:
            p.current_submission = None
        self._log(f"➡️ Round {self.round_num} — new letters: {''.join(self.current_letters)}")

    def _tone(self, best_points: int) -> str:
        if best_points >= 31:
            return "red"
        if best_points >= 21:
            return "yellow"
        return "green"

    # ------------------------------------------------------------------
    # Lobby
    # ------------------------------------------------------------------

    def join(self, username: str) -> tuple[bool, str, Optional[str]]:
        """Returns (ok, token_or_error, final_username)."""
        if self.status == "finished":
            return False, "Game is finished.", None

        for p in self.players:
            if p.username == username and not p.active:
                p.active = True
                p.current_submission = None
                self._log(f"↩️ {p.username} rejoined.")
                return True, p.token, p.username

        if len(self._active_players()) >= self.max_players:
            return False, "Game is full.", None

        # Deduplicate username
        existing = {p.username for p in self._active_players()}
        final_username = username
        if final_username in existing:
            suffix = 2
            while f"{username}{suffix}" in existing:
                suffix += 1
            final_username = f"{username}{suffix}"

        token = str(uuid.uuid4())
        idx = len(self.players)
        p = PlayerState(final_username, token, idx)
        self.players.append(p)
        self.token_map[token] = idx
        self._log(f"👋 {final_username} joined.")

        # Auto-start if lobby fills
        if self.status == "waiting" and len(self._active_players()) == self.max_players:
            self._start_game()

        return True, token, final_username

    def start(self, token: str) -> tuple[bool, str]:
        """Creator manually starts the game."""
        player = self._get_player_by_token(token)
        if player is None:
            return False, "Invalid token."
        if not player.active:
            return False, "Player has left the game."
        if player.join_index != 0:
            return False, "Only the creator can start the game."
        if self.status != "waiting":
            return False, "Game already started."
        if len(self._active_players()) < 1:
            return False, "Need at least 1 active player to start."
        self._start_game()
        return True, "ok"

    def _start_game(self) -> None:
        self.status = "playing"
        self._log("🚀 Game started!")
        self._spin_rack()

    # ------------------------------------------------------------------
    # Play / Pass
    # ------------------------------------------------------------------

    def play(self, token: str, word: str) -> tuple[bool, str]:
        player = self._get_player_by_token(token)
        if player is None:
            return False, "Invalid token."
        if not player.active:
            return False, "Player has left the game."
        if self.status != "playing":
            return False, "Game is not active."
        if self.meta_round_banner is not None:
            return False, "Meta-round banner is active; call /continue first."
        if player.current_submission is not None:
            return False, "Already submitted this round."

        word_upper = word.upper()
        ok, joker_letter, err = validate_word(word_upper, self.current_letters, self.tile_values)
        if not ok:
            return False, err or "Invalid word."

        scored = score_word(word_upper, self.tile_values, joker_letter)
        player.current_submission = {
            "word": word_upper,
            **scored,
        }
        self._log(f"🤫 {player.username} submitted.")

        if self._submitted_count() == len(self._active_players()):
            self._resolve_round()

        return True, "ok"

    def pass_turn(self, token: str) -> tuple[bool, str]:
        player = self._get_player_by_token(token)
        if player is None:
            return False, "Invalid token."
        if not player.active:
            return False, "Player has left the game."
        if self.status != "playing":
            return False, "Game is not active."
        if self.meta_round_banner is not None:
            return False, "Meta-round banner is active; call /continue first."
        if player.current_submission is not None:
            return False, "Already submitted this round."

        player.current_submission = {
            "word": None,
            "points": 0,
            "base_points": 0,
            "length_bonus": 0,
            "joker_letter": None,
            "joker_repeat_penalty": 0,
            "passed": True,
        }
        self._log(f"⏭️ {player.username} passed.")

        if self._submitted_count() == len(self._active_players()):
            self._resolve_round()

        return True, "ok"

    def check_word(self, token: str, word: str) -> tuple[bool, dict]:
        player = self._get_player_by_token(token)
        if player is None:
            return False, {"error": "Invalid token."}
        if not player.active:
            return False, {"error": "Player has left the game."}

        word_upper = word.upper()
        analysis = analyze_word(word_upper, self.current_letters, self.tile_values)
        if not analysis["ok"]:
            return True, {
                "word": word_upper,
                "status": analysis["code"],
                "message": analysis["message"],
                "points": 0,
            }

        scored = score_word(word_upper, self.tile_values, analysis["joker_letter"])
        return True, {
            "word": word_upper,
            "status": "valid",
            "message": "Good word.",
            "points": scored["points"],
        }

    # ------------------------------------------------------------------
    # Round resolution
    # ------------------------------------------------------------------

    def _resolve_round(self) -> None:
        """Called when all players have submitted. Scores, records, checks win."""
        results = []
        for p in self._active_players():
            sub = p.current_submission
            if sub.get("passed"):
                word_display = None
                pts = 0
            else:
                word_display = sub["word"]
                pts = sub["points"]

            p.score += pts

            # Record in per-player history
            history_entry = {
                "meta_round": self.meta_round,
                "round": self.round_num,
                "word": word_display,
                "letters": list(self.current_letters),
                "tile_values": dict(self.tile_values),
                "points": pts,
                "base_points": sub["base_points"],
                "length_bonus": sub["length_bonus"],
                "joker_letter": sub["joker_letter"],
                "joker_repeat_penalty": sub["joker_repeat_penalty"],
            }
            p.history.append(history_entry)

            results.append({
                "username": p.username,
                "word": word_display,
                "points": pts,
                "base_points": sub["base_points"],
                "length_bonus": sub["length_bonus"],
                "joker_letter": sub["joker_letter"],
                "joker_repeat_penalty": sub["joker_repeat_penalty"],
            })

        # Best word this round
        scored_results = [r for r in results if r["word"] is not None]
        if scored_results:
            best_pts = max(r["points"] for r in scored_results)
            best_players = [r["username"] for r in scored_results if r["points"] == best_pts]
            best_words = [r["word"] for r in scored_results if r["points"] == best_pts]
        else:
            best_pts = 0
            best_players = []
            best_words = []

        if best_players:
            headline = f"Best round: {best_players[0]} with {best_words[0]} for {best_pts} pts"
        else:
            headline = "Everyone passed this round."

        detail_letters = " ".join(self.current_letters)
        tone = self._tone(best_pts)

        summary = {
            "meta_round": self.meta_round,
            "round": self.round_num,
            "letters": list(self.current_letters),
            "tile_values": dict(self.tile_values),
            "headline": headline,
            "detail": f"Board: {detail_letters}",
            "best_points": best_pts,
            "best_players": best_players,
            "best_words": best_words,
            "tone": tone,
            "results": results,
        }
        self.last_round_summary = summary
        self.round_history.append(summary)

        words_str = ", ".join(
            f"{r['username']}:{r['word'] or 'PASS'}({r['points']})" for r in results
        )
        self._log(f"📋 Round {self.round_num} resolved — {words_str}")

        # Check for meta-round win
        winners = [p for p in self._active_players() if p.score >= self.score_target]
        if winners:
            self._end_meta_round(winners)
        else:
            self._spin_rack()

    # ------------------------------------------------------------------
    # Meta-round / match end
    # ------------------------------------------------------------------

    def _end_meta_round(self, contenders: list[PlayerState]) -> None:
        # Winner = highest score; tie → lower join_index
        meta_winner = max(
            self._active_players(),
            key=lambda p: (p.score, -p.join_index),
        )
        meta_winner.meta_wins += 1
        self._log(f"🎯 {meta_winner.username} wins Meta-Round {self.meta_round}!")

        scores_snapshot = [
            {"username": p.username, "score": p.score, "meta_wins": p.meta_wins}
            for p in self._active_players()
        ]

        # Reset scores
        for p in self._active_players():
            p.score = 0

        if self.meta_round >= self.num_meta_rounds:
            # Last meta-round → go straight to finished
            self._finish_game()
        else:
            # Set banner; wait for /continue
            next_mr = self.meta_round + 1
            self.meta_round_banner = {
                "winner": meta_winner.username,
                "meta_round": self.meta_round,
                "next_meta_round": next_mr,
                "headline": f"{meta_winner.username} wins Meta-Round {self.meta_round}!",
                "detail": f"Continue when you're ready for Meta-Round {next_mr}.",
                "continue_label": f"Start Meta-Round {next_mr}",
                "scores": scores_snapshot,
            }

    def _finish_game(self) -> None:
        self.status = "finished"
        # Match winner = most meta_wins; tie → lower join_index
        match_winner = max(
            self._active_players(),
            key=lambda p: (p.meta_wins, -p.join_index),
        )
        self.winner = match_winner.username
        self._log(f"🏆 {match_winner.username} wins the match!")

    # ------------------------------------------------------------------
    # Leave / Continue / Rematch
    # ------------------------------------------------------------------

    def leave(self, token: str) -> tuple[bool, str]:
        player = self._get_player_by_token(token)
        if player is None:
            return False, "Invalid token."
        if not player.active:
            return False, "Player already left the game."
        if self.status == "finished":
            return False, "Game is already finished."

        player.active = False
        player.current_submission = None
        self._log(f"👋 {player.username} left the game.")

        active_players = self._active_players()
        if not active_players:
            self.status = "finished"
            self.winner = None
            self.meta_round_banner = None
            self._log("🛑 Game finished because all players left.")
            return True, "ok"

        if self.status == "playing" and self._submitted_count() == len(active_players):
            self._resolve_round()

        return True, "ok"

    def continue_game(self, token: str) -> tuple[bool, str]:
        player = self._get_player_by_token(token)
        if player is None:
            return False, "Invalid token."
        if not player.active:
            return False, "Player has left the game."
        if self.meta_round_banner is None:
            return False, "No meta-round banner to continue from."

        self.meta_round = self.meta_round_banner["next_meta_round"]
        self.meta_round_banner = None
        self.round_num = 0
        self._log(f"▶️ Meta-Round {self.meta_round} started.")
        self._spin_rack()
        return True, "ok"

    def rematch(self, token: str) -> tuple[bool, str]:
        player = self._get_player_by_token(token)
        if player is None:
            return False, "Invalid token."
        if not player.active:
            return False, "Player has left the game."
        if self.status != "finished":
            return False, "Can only rematch when the game is finished."

        # Reset all game state but keep players and settings
        for p in self.players:
            p.score = 0
            p.meta_wins = 0
            p.history = []
            p.current_submission = None

        self.status = "playing"
        self.meta_round = 1
        self.round_num = 0
        self.round_history = []
        self.last_round_summary = None
        self.meta_round_banner = None
        self.winner = None
        self.log = []
        self._log("🔄 Rematch started!")
        self._spin_rack()
        return True, "ok"

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def send_chat(self, token: str, message: str) -> tuple[bool, str]:
        player = self._get_player_by_token(token)
        if player is None:
            return False, "Invalid token."
        if not player.active:
            return False, "Player has left the game."
        message = message[:200]
        self.chat.append({"username": player.username, "text": message})
        if len(self.chat) > 40:
            self.chat = self.chat[-40:]
        return True, "ok"

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        submitted_players = [
            p.username for p in self._active_players() if p.current_submission is not None
        ]
        return {
            "game_id": self.game_id,
            "status": self.status,
            "num_meta_rounds": self.num_meta_rounds,
            "meta_round": self.meta_round,
            "round_num": self.round_num,
            "score_target": self.score_target,
            "max_players": self.max_players,
            "players": [p.to_dict() for p in self.players],
            "current_letters": self.current_letters,
            "tile_values": self.tile_values,
            "submitted_players": submitted_players,
            "meta_round_banner": self.meta_round_banner,
            "winner": self.winner,
            "log": self.log,
            "chat": self.chat,
            "last_round_summary": self.last_round_summary,
            "round_history": self.round_history,
        }

    def is_expired(self) -> bool:
        return time.time() - self.created_at > GAME_TTL
