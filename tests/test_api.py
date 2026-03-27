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

        joined = self.client.post(f"/flux/{self.game_id}/join", json={"username": "bob"})
        joined.raise_for_status()

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


if __name__ == "__main__":
    unittest.main()
