import unittest

from game import FluxGame, analyze_word, score_word, set_dictionary


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


class ScoreWordTests(unittest.TestCase):
    def test_joker_substitution_scores_once(self):
        scored = score_word("BBBBARS", {"A": 3, "R": 4, "S": 1, "*": 7}, "B")
        self.assertEqual(scored["base_points"], 36)
        self.assertEqual(scored["joker_repeat_penalty"], 21)
        self.assertEqual(scored["points"], 15)

    def test_repeated_joker_letter_contributes_only_once_total(self):
        scored = score_word("ZIZZ", {"I": 3, "*": 7}, "Z")
        self.assertEqual(scored["base_points"], 24)
        self.assertEqual(scored["joker_repeat_penalty"], 14)
        self.assertEqual(scored["points"], 10)


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

    def test_rejoin_with_code_rotates_token_and_restores_player(self):
        bob = next(p for p in self.game.players if p.username == "bob")
        old_token = bob.token
        self.game.leave(old_token)
        ok, result, msg = self.game.rejoin_with_code("bob", bob.rejoin_code)
        self.assertTrue(ok)
        self.assertIsNone(msg)
        self.assertEqual(result["username"], "bob")
        self.assertNotEqual(result["player_token"], old_token)
        self.assertTrue(bob.active)

    def test_game_finishes_when_everyone_leaves(self):
        self.game.leave(self.bob_token)
        ok, msg = self.game.leave("tok-alice")
        self.assertTrue(ok)
        self.assertEqual(msg, "ok")
        self.assertEqual(self.game.status, "finished")
        self.assertIsNone(self.game.winner)


class BotGameTests(unittest.TestCase):
    def setUp(self):
        set_dictionary({"CARS", "STAR", "SCAR", "RATS"}, "test")

    def test_bot_match_adds_bot_and_autostarts(self):
        game = FluxGame(
            game_id="BOT12345",
            creator_token="tok-alice",
            username="alice",
            num_meta_rounds=1,
            score_target=100,
            max_players=2,
            vs_bot=True,
        )
        self.assertEqual(game.status, "playing")
        self.assertTrue(game.vs_bot)
        self.assertEqual(len(game.players), 2)
        bot = next(p for p in game.players if p.is_bot)
        self.assertEqual(bot.username, "MEATGRINDER-7")
        self.assertIsNotNone(bot.current_submission)

    def test_bot_match_rejects_human_join(self):
        game = FluxGame(
            game_id="BOT12345",
            creator_token="tok-alice",
            username="alice",
            num_meta_rounds=1,
            score_target=100,
            max_players=2,
            vs_bot=True,
        )
        ok, msg, username = game.join("bob")
        self.assertFalse(ok)
        self.assertEqual(msg, "This is a bot match.")
        self.assertIsNone(username)

    def test_bot_match_allows_original_player_to_rejoin(self):
        game = FluxGame(
            game_id="BOT12345",
            creator_token="tok-alice",
            username="alice",
            num_meta_rounds=1,
            score_target=100,
            max_players=2,
            vs_bot=True,
        )
        ok, msg = game.leave("tok-alice")
        self.assertTrue(ok)
        ok, token, username = game.join("alice")
        self.assertTrue(ok)
        self.assertEqual(token, "tok-alice")
        self.assertEqual(username, "alice")


if __name__ == "__main__":
    unittest.main()
