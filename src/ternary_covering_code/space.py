"""Finite ternary Hamming-space primitives."""

from __future__ import annotations

from itertools import combinations, product
from math import comb
from typing import Iterable, Sequence, Tuple


Q = 3
N = 7
RADIUS = 3
WORD_COUNT = Q**N
Word = Tuple[int, ...]


def all_words(q: int = Q, n: int = N) -> Tuple[Word, ...]:
    return tuple(product(range(q), repeat=n))


def encode(word: Sequence[int], q: int = Q) -> int:
    value = 0
    for symbol in word:
        if not 0 <= symbol < q:
            raise ValueError(f"Symbol {symbol} is outside 0..{q - 1}.")
        value = value * q + symbol
    return value


def decode(value: int, q: int = Q, n: int = N) -> Word:
    if not 0 <= value < q**n:
        raise ValueError(f"Value {value} is outside 0..{q**n - 1}.")
    result = [0] * n
    for index in range(n - 1, -1, -1):
        result[index] = value % q
        value //= q
    return tuple(result)


def hamming_distance(left: Sequence[int], right: Sequence[int]) -> int:
    if len(left) != len(right):
        raise ValueError("Words must have the same length.")
    return sum(a != b for a, b in zip(left, right))


def ball(center: Sequence[int], radius: int = RADIUS, q: int = Q) -> Tuple[Word, ...]:
    center_tuple = tuple(center)
    points = []
    for changed_count in range(radius + 1):
        for positions in combinations(range(len(center_tuple)), changed_count):
            for changes in product(range(1, q), repeat=changed_count):
                point = list(center_tuple)
                for position, change in zip(positions, changes):
                    point[position] = (point[position] + change) % q
                points.append(tuple(point))
    return tuple(points)


def ball_size(n: int = N, q: int = Q, radius: int = RADIUS) -> int:
    return sum(comb(n, changed) * (q - 1) ** changed for changed in range(radius + 1))


def parse_word(text: str, q: int = Q, n: int = N) -> Word:
    stripped = text.strip()
    if len(stripped) != n:
        raise ValueError(f"Expected {n} symbols, found {len(stripped)}.")
    word = tuple(int(symbol) for symbol in stripped)
    encode(word, q=q)
    return word


def format_word(word: Iterable[int]) -> str:
    return "".join(str(symbol) for symbol in word)
