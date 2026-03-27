"""
Flux — FastAPI server.
Deploy to HuggingFace Spaces (Docker SDK, port 7860).
"""

from __future__ import annotations

import os
import random
import string
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from game import FluxGame, set_dictionary, get_dictionary_info

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Flux")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory game store
# ---------------------------------------------------------------------------

games: dict[str, FluxGame] = {}


def _board_state(game: FluxGame) -> str:
    if game.status == "waiting":
        return "waiting"
    if game.status == "finished":
        return "finished"
    return "active"


def _game_summary(game: FluxGame) -> dict:
    active_players = [p for p in game.players if getattr(p, "active", True)]
    creator = min(game.players, key=lambda p: p.join_index).username if game.players else None
    return {
        "game_id": game.game_id,
        "creator": creator,
        "state": _board_state(game),
        "round_num": game.round_num,
        "meta_round": game.meta_round,
        "num_meta_rounds": game.num_meta_rounds,
        "active_players": len(active_players),
        "max_players": game.max_players,
        "score_target": game.score_target,
        "can_join": game.status != "finished" and len(active_players) < game.max_players,
    }


def _get_game(game_id: str) -> FluxGame:
    g = games.get(game_id.upper())
    if g is None:
        raise HTTPException(status_code=404, detail="Game not found.")
    return g


def _purge_expired() -> None:
    expired = [gid for gid, g in games.items() if g.is_expired()]
    for gid in expired:
        del games[gid]


def _generate_game_id() -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        gid = "".join(random.choices(chars, k=8))
        if gid not in games:
            return gid


# ---------------------------------------------------------------------------
# Dictionary loading
# ---------------------------------------------------------------------------

def load_dictionary() -> None:
    words: set[str] = set()
    source = "none"

    sowpods_path = os.path.join(os.path.dirname(__file__), "sowpods.txt")
    if os.path.exists(sowpods_path):
        with open(sowpods_path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip().upper()
                if w.isalpha() and 2 <= len(w) <= 20:
                    words.add(w)
        if len(words) >= 50_000:
            source = "sowpods"

    if source == "none":
        try:
            import nltk
            try:
                nltk.data.find("corpora/words")
            except LookupError:
                nltk.download("words", quiet=True)
            from nltk.corpus import words as nltk_words
            for w in nltk_words.words():
                w = w.upper()
                if w.isalpha() and 2 <= len(w) <= 20:
                    words.add(w)
            source = "nltk"
        except Exception as e:
            print(f"Warning: could not load NLTK words corpus: {e}")

    set_dictionary(words, source)
    size, src = get_dictionary_info()
    print(f"Dictionary loaded: {size} words from {src}")


load_dictionary()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateGameRequest(BaseModel):
    username: str
    num_meta_rounds: int = 3
    score_target: int = 200
    max_players: int = 2


class JoinRequest(BaseModel):
    username: str


class RejoinRequest(BaseModel):
    username: str
    rejoin_code: str


class TokenRequest(BaseModel):
    player_token: str


class PlayRequest(BaseModel):
    player_token: str
    word: str


class CheckWordRequest(BaseModel):
    player_token: str
    word: str


class ChatRequest(BaseModel):
    player_token: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/flux")
def list_games():
    _purge_expired()
    ordered_games = sorted(games.values(), key=lambda g: g.created_at, reverse=True)
    return {"games": [_game_summary(game) for game in ordered_games]}

@app.post("/flux")
def create_game(req: CreateGameRequest):
    # Validate settings
    if req.num_meta_rounds not in (1, 3, 5):
        raise HTTPException(400, "num_meta_rounds must be 1, 3, or 5.")
    if req.score_target not in (100, 200, 500, 1000):
        raise HTTPException(400, "score_target must be 100, 200, 500, or 1000.")
    if not (2 <= req.max_players <= 6):
        raise HTTPException(400, "max_players must be between 2 and 6.")
    if not req.username.strip():
        raise HTTPException(400, "Username required.")

    _purge_expired()

    game_id = _generate_game_id()
    token = str(uuid.uuid4())
    game = FluxGame(
        game_id=game_id,
        creator_token=token,
        username=req.username.strip()[:30],
        num_meta_rounds=req.num_meta_rounds,
        score_target=req.score_target,
        max_players=req.max_players,
    )
    games[game_id] = game
    access = game.player_access_dict(token) or {}
    return {"game_id": game_id, "player_token": token, **access}


@app.post("/flux/{game_id}/join")
def join_game(game_id: str, req: JoinRequest):
    game = _get_game(game_id)
    if not req.username.strip():
        raise HTTPException(400, "Username required.")
    ok, result, final_username = game.join(req.username.strip()[:30])
    if not ok:
        raise HTTPException(400, result)
    access = game.player_access_dict(result) or {}
    return {"game_id": game.game_id, "player_token": result, "username": final_username, **access}


@app.post("/flux/{game_id}/rejoin")
def rejoin_game(game_id: str, req: RejoinRequest):
    game = _get_game(game_id)
    if not req.username.strip():
        raise HTTPException(400, "Username required.")
    if not req.rejoin_code.strip():
        raise HTTPException(400, "Rejoin code required.")
    ok, result, msg = game.rejoin_with_code(req.username.strip()[:30], req.rejoin_code)
    if not ok:
        raise HTTPException(400, msg or "Could not rejoin game.")
    return {"game_id": game.game_id, **(result or {})}


@app.post("/flux/{game_id}/start")
def start_game(game_id: str, req: TokenRequest):
    game = _get_game(game_id)
    ok, msg = game.start(req.player_token)
    if not ok:
        code = 403 if "token" in msg.lower() or "creator" in msg.lower() else 400
        raise HTTPException(code, msg)
    return game.to_dict()


@app.get("/flux/{game_id}")
def get_game(game_id: str):
    game = _get_game(game_id)
    return game.to_dict()


@app.post("/flux/{game_id}/play")
def play_word(game_id: str, req: PlayRequest):
    game = _get_game(game_id)
    ok, msg = game.play(req.player_token, req.word)
    if not ok:
        code = 403 if msg == "Invalid token." else 400
        raise HTTPException(code, msg)
    return game.to_dict()


@app.post("/flux/{game_id}/pass")
def pass_turn(game_id: str, req: TokenRequest):
    game = _get_game(game_id)
    ok, msg = game.pass_turn(req.player_token)
    if not ok:
        code = 403 if msg == "Invalid token." else 400
        raise HTTPException(code, msg)
    return game.to_dict()


@app.post("/flux/{game_id}/leave")
def leave_game(game_id: str, req: TokenRequest):
    game = _get_game(game_id)
    ok, msg = game.leave(req.player_token)
    if not ok:
        code = 403 if msg == "Invalid token." else 400
        raise HTTPException(code, msg)
    return {"ok": True}


@app.post("/flux/{game_id}/access")
def player_access(game_id: str, req: TokenRequest):
    game = _get_game(game_id)
    access = game.player_access_dict(req.player_token)
    if access is None:
        raise HTTPException(403, "Invalid token.")
    return access


@app.post("/flux/{game_id}/check_word")
def check_word(game_id: str, req: CheckWordRequest):
    game = _get_game(game_id)
    ok, result = game.check_word(req.player_token, req.word)
    if not ok:
        raise HTTPException(403, result.get("error", "Invalid token."))
    return result


@app.post("/flux/{game_id}/continue")
def continue_game(game_id: str, req: TokenRequest):
    game = _get_game(game_id)
    ok, msg = game.continue_game(req.player_token)
    if not ok:
        code = 403 if msg == "Invalid token." else 400
        raise HTTPException(code, msg)
    return game.to_dict()


@app.post("/flux/{game_id}/rematch")
def rematch(game_id: str, req: TokenRequest):
    game = _get_game(game_id)
    ok, msg = game.rematch(req.player_token)
    if not ok:
        code = 403 if msg == "Invalid token." else 400
        raise HTTPException(code, msg)
    return game.to_dict()


@app.post("/flux/{game_id}/chat")
def chat(game_id: str, req: ChatRequest):
    game = _get_game(game_id)
    ok, msg = game.send_chat(req.player_token, req.message)
    if not ok:
        raise HTTPException(403, msg)
    return {"ok": True}


@app.get("/health")
def health():
    size, source = get_dictionary_info()
    return {
        "status": "ok",
        "active_games": len(games),
        "dictionary_size": size,
        "dictionary_source": source,
    }
