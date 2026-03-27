import unittest

from game import FluxGame, analyze_word, set_dictionary


class AnalyzeWordTests(unittest.TestCase):
    def setUp(self):
        set_dictionary({"CARS", "BARS", "BIRD", "STAR"}, "test")

    def test_valid_word_returns_valid_status(self):
        result = analyze_word("CARS", list("CARTS"), {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["code"], "valid")
        self.assertEqual(result["message"], "Good word.")

    def test_missing_letters_returns_specific_status(self):
        result = analyze_word("BARS", list("CARTS"), {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "missing_letters")
        self.assertEqual(result["message"], "You don't have the letters.")

    def test_not_in_dictionary_returns_specific_status(self):
        result = analyze_word("ZZZ", list("CARTS*"), {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "not_in_dictionary")
        self.assertEqual(result["message"], "Not a word.")

    def test_single_missing_family_can_use_joker(self):
        result = analyze_word("BARS", list("CARTS*"), {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["code"], "valid")
        self.assertEqual(result["joker_letter"], "B")


class LeaveRejoinTests(unittest.TestCase):
    def setUp(self):
        self.game = FluxGame(
            game_id="TEST1234",
            creator_token="tok-alice",
            username="alice",
            num_meta_rounds=1,
            score_target=100,
            max_players=3,
        )
        ok, token, _ = self.game.join("bob")
        self.assertTrue(ok)
        self.bob_token = token

    def test_leave_marks_player_inactive(self):
        ok, msg = self.game.leave(self.bob_token)
        self.assertTrue(ok)
        self.assertEqual(msg, "ok")
        self.assertFalse(next(p for p in self.game.players if p.username == "bob").active)

    def test_rejoin_restores_same_token_and_player_slot(self):
        self.game.leave(self.bob_token)
        ok, token, username = self.game.join("bob")
        self.assertTrue(ok)
        self.assertEqual(token, self.bob_token)
        self.assertEqual(username, "bob")
        self.assertTrue(next(p for p in self.game.players if p.username == "bob").active)

    def test_game_finishes_when_everyone_leaves(self):
        self.game.leave(self.bob_token)
        ok, msg = self.game.leave("tok-alice")
        self.assertTrue(ok)
        self.assertEqual(msg, "ok")
        self.assertEqual(self.game.status, "finished")
        self.assertIsNone(self.game.winner)


if __name__ == "__main__":
    unittest.main()
