import unittest

from ternary_covering_code.space import (
    N,
    Q,
    RADIUS,
    WORD_COUNT,
    all_words,
    ball,
    ball_size,
    decode,
    encode,
)


class SpaceTests(unittest.TestCase):
    def test_word_enumeration(self):
        words = all_words()
        self.assertEqual(len(words), WORD_COUNT)
        self.assertEqual(len(set(words)), WORD_COUNT)

    def test_encode_decode_round_trip(self):
        for value in range(WORD_COUNT):
            self.assertEqual(encode(decode(value)), value)

    def test_ball_size(self):
        self.assertEqual(ball_size(), 379)
        points = ball((0,) * N, radius=RADIUS, q=Q)
        self.assertEqual(len(points), 379)
        self.assertEqual(len(set(points)), 379)


if __name__ == "__main__":
    unittest.main()
