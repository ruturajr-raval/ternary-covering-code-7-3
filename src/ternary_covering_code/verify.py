"""Independent construction verification paths."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations, product
from pathlib import Path
from typing import Sequence, Tuple

from .space import N, Q, RADIUS, Word, all_words, hamming_distance, parse_word


@dataclass(frozen=True)
class Verification:
    code_size: int
    ambient_words: int
    maximum_nearest_distance: int
    generated_covered_words: int
    distance_distribution: Tuple[Tuple[int, int], ...]


def load_code(path: Path) -> Tuple[Word, ...]:
    code = tuple(
        parse_word(line)
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if len(code) != len(set(code)):
        raise ValueError("The code contains duplicate words.")
    return code


def direct_distances(code: Sequence[Word]) -> Tuple[int, ...]:
    if not code:
        raise ValueError("The code must be nonempty.")
    return tuple(
        min(hamming_distance(word, center) for center in code)
        for word in all_words()
    )


def generated_coverage(code: Sequence[Word]) -> int:
    covered = set()
    for center in code:
        for changed_count in range(RADIUS + 1):
            for positions in combinations(range(N), changed_count):
                for changes in product(range(1, Q), repeat=changed_count):
                    word = list(center)
                    for position, change in zip(positions, changes):
                        word[position] = (word[position] + change) % Q
                    covered.add(tuple(word))
    return len(covered)


def verify(code: Sequence[Word]) -> Verification:
    distances = direct_distances(code)
    distribution = Counter(distances)
    generated = generated_coverage(code)
    ambient = Q**N
    maximum = max(distances)

    if maximum > RADIUS:
        raise ValueError(f"The code has covering radius at least {maximum}.")
    if generated != ambient:
        raise ValueError(
            f"Generated balls cover {generated} words instead of {ambient}."
        )

    return Verification(
        code_size=len(code),
        ambient_words=ambient,
        maximum_nearest_distance=maximum,
        generated_covered_words=generated,
        distance_distribution=tuple(sorted(distribution.items())),
    )
