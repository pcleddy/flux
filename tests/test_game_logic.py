import unittest

from game import analyze_word, set_dictionary


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


if __name__ == "__main__":
    unittest.main()
