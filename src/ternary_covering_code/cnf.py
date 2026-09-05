"""Deterministic set-cover CNF generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from .space import N, Q, RADIUS, all_words, hamming_distance


@dataclass(frozen=True)
class Formula:
    variable_count: int
    clauses: Tuple[Tuple[int, ...], ...]


def sequential_at_most(
    variables: Sequence[int],
    limit: int,
    next_variable: int,
) -> Tuple[List[List[int]], int, Dict[Tuple[int, int], int]]:
    count = len(variables)
    if limit < 0:
        return [[]], next_variable, {}
    if limit == 0:
        return [[-variable] for variable in variables], next_variable, {}
    if count <= limit:
        return [], next_variable, {}

    counters: Dict[Tuple[int, int], int] = {}
    for row in range(1, count):
        for column in range(1, limit + 1):
            counters[row, column] = next_variable
            next_variable += 1

    clauses: List[List[int]] = [[-variables[0], counters[1, 1]]]
    for row in range(2, count):
        variable = variables[row - 1]
        clauses.append([-variable, counters[row, 1]])
        clauses.append([-counters[row - 1, 1], counters[row, 1]])
        for column in range(2, limit + 1):
            clauses.append(
                [
                    -variable,
                    -counters[row - 1, column - 1],
                    counters[row, column],
                ]
            )
            clauses.append(
                [-counters[row - 1, column], counters[row, column]]
            )

    for row in range(2, count + 1):
        clauses.append(
            [-variables[row - 1], -counters[row - 1, limit]]
        )

    return clauses, next_variable, counters


def covering_formula(limit: int, anchor_zero: bool = True) -> Formula:
    words = all_words()
    primary_count = len(words)
    clauses: List[List[int]] = []

    for target in words:
        clauses.append(
            [
                center_index + 1
                for center_index, center in enumerate(words)
                if hamming_distance(center, target) <= RADIUS
            ]
        )

    if anchor_zero:
        clauses.append([1])
        cardinality_variables = list(range(2, primary_count + 1))
        cardinality_limit = limit - 1
    else:
        cardinality_variables = list(range(1, primary_count + 1))
        cardinality_limit = limit

    cardinality, next_variable, _ = sequential_at_most(
        cardinality_variables,
        cardinality_limit,
        primary_count + 1,
    )
    clauses.extend(cardinality)
    return Formula(
        variable_count=next_variable - 1,
        clauses=tuple(tuple(clause) for clause in clauses),
    )


def write_dimacs(path: Path, formula: Formula, limit: int) -> None:
    with path.open("w", encoding="ascii", newline="\n") as handle:
        handle.write(
            f"c q={Q} n={N} radius={RADIUS} limit={limit} "
            "anchored-center=0000000\n"
        )
        handle.write(
            f"p cnf {formula.variable_count} {len(formula.clauses)}\n"
        )
        for clause in formula.clauses:
            handle.write(" ".join(str(literal) for literal in clause))
            handle.write(" 0\n")
