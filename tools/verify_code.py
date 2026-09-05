#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from ternary_covering_code.verify import load_code, verify


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("code", type=Path)
    args = parser.parse_args()

    result = verify(load_code(args.code))
    print(f"code_size={result.code_size}")
    print(f"ambient_words={result.ambient_words}")
    print(f"covering_radius={result.maximum_nearest_distance}")
    print(f"generated_covered_words={result.generated_covered_words}")
    print(f"distance_distribution={dict(result.distance_distribution)}")


if __name__ == "__main__":
    main()
