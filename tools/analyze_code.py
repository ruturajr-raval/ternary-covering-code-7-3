#!/usr/bin/env python3

from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
from pathlib import Path

from ternary_covering_code.space import all_words, format_word, hamming_distance
from ternary_covering_code.verify import load_code


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("code", type=Path)
    args = parser.parse_args()

    code = load_code(args.code)
    space = all_words()
    nearest = tuple(
        min(hamming_distance(word, center) for center in code)
        for word in space
    )
    uncovered = tuple(
        word for word, distance in zip(space, nearest) if distance > 3
    )
    pair_distances = Counter(
        hamming_distance(left, right)
        for left, right in combinations(code, 2)
    )
    uncovered_pair_distances = Counter(
        hamming_distance(left, right)
        for left, right in combinations(uncovered, 2)
    )
    repair_centers = tuple(
        center
        for center in space
        if all(hamming_distance(center, word) <= 3 for word in uncovered)
    )

    print(f"code_size={len(code)}")
    print(f"maximum_nearest_distance={max(nearest)}")
    print(f"nearest_distance_distribution={dict(Counter(nearest))}")
    print(f"uncovered_count={len(uncovered)}")
    print(f"uncovered_words={[format_word(word) for word in uncovered]}")
    print(f"code_pair_distances={dict(sorted(pair_distances.items()))}")
    print(
        "uncovered_pair_distances="
        f"{dict(sorted(uncovered_pair_distances.items()))}"
    )
    print(f"repair_center_count={len(repair_centers)}")


if __name__ == "__main__":
    main()
