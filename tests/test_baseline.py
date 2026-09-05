import unittest
from pathlib import Path

from ternary_covering_code.verify import load_code, verify


ROOT = Path(__file__).resolve().parents[1]


class BaselineTests(unittest.TestCase):
    def test_retained_code_covers(self):
        code = load_code(ROOT / "data" / "baseline_code_12.txt")
        result = verify(code)
        self.assertEqual(result.code_size, 12)
        self.assertEqual(result.ambient_words, 2187)
        self.assertEqual(result.maximum_nearest_distance, 3)
        self.assertEqual(result.generated_covered_words, 2187)
        self.assertEqual(
            dict(result.distance_distribution),
            {0: 12, 1: 168, 2: 830, 3: 1177},
        )


if __name__ == "__main__":
    unittest.main()
