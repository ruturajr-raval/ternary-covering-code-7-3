import unittest
from pathlib import Path

from ternary_covering_code.space import all_words, hamming_distance
from ternary_covering_code.verify import load_code


ROOT = Path(__file__).resolve().parents[1]


class NearCodeTests(unittest.TestCase):
    def test_seed_101_leaves_six_words(self):
        code = load_code(ROOT / "data" / "search" / "seed_101_best_11.txt")
        uncovered = [
            word
            for word in all_words()
            if min(hamming_distance(word, center) for center in code) > 3
        ]
        self.assertEqual(len(code), 11)
        self.assertEqual(len(uncovered), 6)


if __name__ == "__main__":
    unittest.main()
