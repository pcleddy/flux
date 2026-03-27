import unittest

try:
    from fastapi.testclient import TestClient
    import main
    from game import set_dictionary
except ModuleNotFoundError as exc:  # pragma: no cover - env-dependent skip
    TestClient = None
    main = None
    set_dictionary = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


class CheckWordApiTests(unittest.TestCase):
    def setUp(self):
        if _IMPORT_ERROR is not None:
            raise unittest.SkipTest(f"FastAPI test dependencies are unavailable: {_IMPORT_ERROR}")
        set_dictionary({"CARS", "BARS", "STAR"}, "test")
        main.games.clear()
        self.client = TestClient(main.app)

        created = self.client.post(
            "/flux",
            json={
                "username": "alice",
                "num_meta_rounds": 1,
                "score_target": 100,
                "max_players": 2,
            },
        )
        created.raise_for_status()
        created_data = created.json()
        self.game_id = created_data["game_id"]
        self.alice_token = created_data["player_token"]
        self.assertIn("rejoin_code", created_data)
        self.alice_rejoin_code = created_data["rejoin_code"]

        joined = self.client.post(f"/flux/{self.game_id}/join", json={"username": "bob"})
        joined.raise_for_status()
        self.bob_rejoin_code = joined.json()["rejoin_code"]

        game = main.games[self.game_id]
        game.current_letters = list("CARTS")
        game.tile_values = {"C": 2, "A": 3, "R": 4, "T": 5, "S": 1}

    def test_check_word_returns_valid_status(self):
        resp = self.client.post(
            f"/flux/{self.game_id}/check_word",
            json={"player_token": self.alice_token, "word": "CARS"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "valid")
        self.assertEqual(resp.json()["message"], "Good word.")

    def test_check_word_returns_missing_letters_status(self):
        resp = self.client.post(
            f"/flux/{self.game_id}/check_word",
            json={"player_token": self.alice_token, "word": "BARS"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "missing_letters")
        self.assertEqual(resp.json()["message"], "You don't have the letters.")

    def test_check_word_returns_not_in_dictionary_status(self):
        resp = self.client.post(
            f"/flux/{self.game_id}/check_word",
            json={"player_token": self.alice_token, "word": "ZZZ"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "not_in_dictionary")
        self.assertEqual(resp.json()["message"], "Not a word.")

    def test_leave_marks_player_inactive(self):
        game = main.games[self.game_id]
        bob_token = next(p.token for p in game.players if p.username == "bob")

        resp = self.client.post(
            f"/flux/{self.game_id}/leave",
            json={"player_token": bob_token},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True})
        self.assertFalse(next(p for p in game.players if p.username == "bob").active)

    def test_rejoin_returns_same_token_for_left_player(self):
        game = main.games[self.game_id]
        bob_token = next(p.token for p in game.players if p.username == "bob")

        leave_resp = self.client.post(
            f"/flux/{self.game_id}/leave",
            json={"player_token": bob_token},
        )
        self.assertEqual(leave_resp.status_code, 200)

        rejoin_resp = self.client.post(
            f"/flux/{self.game_id}/join",
            json={"username": "bob"},
        )
        self.assertEqual(rejoin_resp.status_code, 200)
        self.assertEqual(rejoin_resp.json()["player_token"], bob_token)
        self.assertEqual(rejoin_resp.json()["username"], "bob")

    def test_rejoin_with_code_returns_new_token(self):
        game = main.games[self.game_id]
        bob_token = next(p.token for p in game.players if p.username == "bob")

        leave_resp = self.client.post(
            f"/flux/{self.game_id}/leave",
            json={"player_token": bob_token},
        )
        self.assertEqual(leave_resp.status_code, 200)

        rejoin_resp = self.client.post(
            f"/flux/{self.game_id}/rejoin",
            json={"username": "bob", "rejoin_code": self.bob_rejoin_code},
        )
        self.assertEqual(rejoin_resp.status_code, 200)
        self.assertEqual(rejoin_resp.json()["username"], "bob")
        self.assertNotEqual(rejoin_resp.json()["player_token"], bob_token)
        self.assertEqual(rejoin_resp.json()["rejoin_code"], self.bob_rejoin_code)

    def test_game_finishes_when_all_players_leave(self):
        game = main.games[self.game_id]
        bob_token = next(p.token for p in game.players if p.username == "bob")

        self.client.post(f"/flux/{self.game_id}/leave", json={"player_token": bob_token})
        resp = self.client.post(
            f"/flux/{self.game_id}/leave",
            json={"player_token": self.alice_token},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(main.games[self.game_id].status, "finished")

    def test_list_games_returns_board_summary(self):
        resp = self.client.get("/flux")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertIn("games", payload)
        self.assertEqual(len(payload["games"]), 1)
        game = payload["games"][0]
        self.assertEqual(game["game_id"], self.game_id)
        self.assertEqual(game["creator"], "alice")
        self.assertEqual(game["state"], "active")
        self.assertEqual(game["active_players"], 2)
        self.assertTrue(game["can_join"] is False)

    def test_create_game_allows_solo_mode(self):
        resp = self.client.post(
            "/flux",
            json={
                "username": "solo",
                "num_meta_rounds": 1,
                "score_target": 100,
                "max_players": 1,
            },
        )
        self.assertEqual(resp.status_code, 200)
        game_id = resp.json()["game_id"]
        self.assertEqual(main.games[game_id].max_players, 1)

    def test_create_game_with_bot_starts_immediately(self):
        resp = self.client.post(
            "/flux",
            json={
                "username": "solo",
                "num_meta_rounds": 1,
                "score_target": 100,
                "max_players": 1,
                "vs_bot": True,
            },
        )
        self.assertEqual(resp.status_code, 200)
        game_id = resp.json()["game_id"]
        game = main.games[game_id]
        self.assertEqual(game.status, "playing")
        self.assertTrue(game.vs_bot)
        self.assertEqual(game.max_players, 2)
        self.assertEqual(len(game.players), 2)
        self.assertTrue(any(p.is_bot for p in game.players))

    def test_create_game_rejects_bot_without_solo(self):
        resp = self.client.post(
            "/flux",
            json={
                "username": "solo",
                "num_meta_rounds": 1,
                "score_target": 100,
                "max_players": 2,
                "vs_bot": True,
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Solo", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main()
