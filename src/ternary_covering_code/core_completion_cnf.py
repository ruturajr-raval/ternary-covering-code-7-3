"""Independent SAT encoding for completion of the fixed plateau core.

The eight fixed codewords are treated as constants.  Primary variable
``encode(word) + 1`` selects an added center, and one slack variable is
assigned to each point not covered by the fixed core.  For every such point,
the formula requires either a selected radius-3 center or its slack variable.
Two sequential counters independently enforce:

* at most three added centers; and
* at most ``residual_limit`` uncovered core holes.

This module does not import or call the plateau mask search.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Sequence, Tuple

from .cnf import sequential_at_most
from .space import (
    N,
    Q,
    RADIUS,
    WORD_COUNT,
    Word,
    all_words,
    ball,
    encode,
    format_word,
    hamming_distance,
    parse_word,
)


Clause = Tuple[int, ...]
CounterVariable = Tuple[int, int, int]
ADDED_CENTER_LIMIT = 3
FIXED_CORE = tuple(
    parse_word(text)
    for text in (
        "0000011",
        "0000102",
        "0000220",
        "0002121",
        "1111022",
        "1111110",
        "1111201",
        "2222000",
    )
)


@dataclass(frozen=True)
class CoreCompletionClauseCounts:
    """Deterministic clause counts by logical constraint group."""

    fixed_core_exclusions: int
    residual_covering: int
    added_center_cardinality: int
    uncovered_hole_cardinality: int

    @property
    def total(self) -> int:
        return (
            self.fixed_core_exclusions
            + self.residual_covering
            + self.added_center_cardinality
            + self.uncovered_hole_cardinality
        )


@dataclass(frozen=True)
class CoreCompletionFormula:
    """CNF formula and complete deterministic encoding metadata."""

    residual_limit: int
    added_center_limit: int
    primary_variable_count: int
    fixed_core: Tuple[Word, ...]
    fixed_core_variables: Tuple[int, ...]
    candidate_centers: Tuple[Word, ...]
    candidate_center_variables: Tuple[int, ...]
    core_holes: Tuple[Word, ...]
    hole_slack_variables: Tuple[int, ...]
    added_center_counter_variables: Tuple[CounterVariable, ...]
    uncovered_hole_counter_variables: Tuple[CounterVariable, ...]
    variable_count: int
    clause_counts: CoreCompletionClauseCounts
    clauses: Tuple[Clause, ...]


@dataclass(frozen=True)
class CoreCompletionModel:
    """Primary and slack selections extracted from a SAT model."""

    added_centers: Tuple[Word, ...]
    uncovered_core_holes: Tuple[Word, ...]


@dataclass(frozen=True)
class _StaticCoreEncoding:
    fixed_core_variables: Tuple[int, ...]
    candidate_centers: Tuple[Word, ...]
    candidate_center_variables: Tuple[int, ...]
    core_holes: Tuple[Word, ...]
    hole_slack_variables: Tuple[int, ...]
    fixed_core_exclusion_clauses: Tuple[Clause, ...]
    residual_covering_clauses: Tuple[Clause, ...]


def primary_variable(word: Sequence[int]) -> int:
    """Return the one-based primary variable for an ambient word."""

    center = tuple(word)
    if len(center) != N:
        raise ValueError(f"Expected a word of length {N}, found {len(center)}.")
    return encode(center) + 1


def _validate_residual_limit(residual_limit: int) -> None:
    if isinstance(residual_limit, bool) or not isinstance(
        residual_limit,
        int,
    ):
        raise TypeError("Residual limit must be an integer.")
    if residual_limit < 0:
        raise ValueError("Residual limit must be nonnegative.")


def _counter_metadata(
    counter: Dict[Tuple[int, int], int],
) -> Tuple[CounterVariable, ...]:
    return tuple(
        (row, column, variable)
        for (row, column), variable in sorted(counter.items())
    )


@lru_cache(maxsize=1)
def _static_core_encoding() -> _StaticCoreEncoding:
    words = all_words()
    fixed_core_set = frozenset(FIXED_CORE)
    fixed_core_variables = tuple(
        primary_variable(center) for center in FIXED_CORE
    )
    candidate_centers = tuple(
        center for center in words if center not in fixed_core_set
    )
    candidate_center_variables = tuple(
        primary_variable(center) for center in candidate_centers
    )
    core_holes = tuple(
        target
        for target in words
        if all(
            hamming_distance(target, center) > RADIUS
            for center in FIXED_CORE
        )
    )
    hole_slack_variables = tuple(
        range(
            WORD_COUNT + 1,
            WORD_COUNT + len(core_holes) + 1,
        )
    )
    fixed_core_exclusion_clauses = tuple(
        (-variable,) for variable in fixed_core_variables
    )

    residual_covering_clauses = []
    for target, slack_variable in zip(
        core_holes,
        hole_slack_variables,
    ):
        covering_variables = tuple(
            sorted(
                primary_variable(center)
                for center in ball(target, radius=RADIUS, q=Q)
                if center not in fixed_core_set
            )
        )
        residual_covering_clauses.append(
            (slack_variable,) + covering_variables
        )

    return _StaticCoreEncoding(
        fixed_core_variables=fixed_core_variables,
        candidate_centers=candidate_centers,
        candidate_center_variables=candidate_center_variables,
        core_holes=core_holes,
        hole_slack_variables=hole_slack_variables,
        fixed_core_exclusion_clauses=fixed_core_exclusion_clauses,
        residual_covering_clauses=tuple(residual_covering_clauses),
    )


def core_completion_formula(
    residual_limit: int,
) -> CoreCompletionFormula:
    """Build the at-most-three completion CNF for the fixed core."""

    _validate_residual_limit(residual_limit)
    static = _static_core_encoding()
    next_variable = static.hole_slack_variables[-1] + 1

    added_center_clauses, next_variable, added_center_counter = (
        sequential_at_most(
            static.candidate_center_variables,
            ADDED_CENTER_LIMIT,
            next_variable,
        )
    )
    uncovered_hole_clauses, next_variable, uncovered_hole_counter = (
        sequential_at_most(
            static.hole_slack_variables,
            residual_limit,
            next_variable,
        )
    )
    frozen_added_center_clauses = tuple(
        tuple(clause) for clause in added_center_clauses
    )
    frozen_uncovered_hole_clauses = tuple(
        tuple(clause) for clause in uncovered_hole_clauses
    )
    clauses = (
        static.fixed_core_exclusion_clauses
        + static.residual_covering_clauses
        + frozen_added_center_clauses
        + frozen_uncovered_hole_clauses
    )
    counts = CoreCompletionClauseCounts(
        fixed_core_exclusions=len(
            static.fixed_core_exclusion_clauses
        ),
        residual_covering=len(static.residual_covering_clauses),
        added_center_cardinality=len(frozen_added_center_clauses),
        uncovered_hole_cardinality=len(
            frozen_uncovered_hole_clauses
        ),
    )
    if counts.total != len(clauses):
        raise AssertionError("Clause accounting does not match the formula.")

    return CoreCompletionFormula(
        residual_limit=residual_limit,
        added_center_limit=ADDED_CENTER_LIMIT,
        primary_variable_count=WORD_COUNT,
        fixed_core=FIXED_CORE,
        fixed_core_variables=static.fixed_core_variables,
        candidate_centers=static.candidate_centers,
        candidate_center_variables=static.candidate_center_variables,
        core_holes=static.core_holes,
        hole_slack_variables=static.hole_slack_variables,
        added_center_counter_variables=_counter_metadata(
            added_center_counter
        ),
        uncovered_hole_counter_variables=_counter_metadata(
            uncovered_hole_counter
        ),
        variable_count=next_variable - 1,
        clause_counts=counts,
        clauses=clauses,
    )


def extract_core_completion_model(
    formula: CoreCompletionFormula,
    model_literals: Iterable[int],
) -> CoreCompletionModel:
    """Extract added centers and declared holes from signed model literals."""

    true_variables = frozenset(
        literal for literal in model_literals if literal > 0
    )
    added_centers = tuple(
        center
        for center, variable in zip(
            formula.candidate_centers,
            formula.candidate_center_variables,
        )
        if variable in true_variables
    )
    uncovered_core_holes = tuple(
        hole
        for hole, variable in zip(
            formula.core_holes,
            formula.hole_slack_variables,
        )
        if variable in true_variables
    )
    return CoreCompletionModel(
        added_centers=added_centers,
        uncovered_core_holes=uncovered_core_holes,
    )


def write_core_completion_dimacs(
    path: Path,
    formula: CoreCompletionFormula,
) -> None:
    """Write the fixed-core completion formula as deterministic DIMACS."""

    counts = formula.clause_counts
    fixed_core = ",".join(
        format_word(center) for center in formula.fixed_core
    )
    slack_start = formula.hole_slack_variables[0]
    slack_end = formula.hole_slack_variables[-1]
    with path.open("w", encoding="ascii", newline="\n") as handle:
        handle.write(
            f"c q={Q} n={N} radius={RADIUS} "
            f"fixed-core-size={len(formula.fixed_core)} "
            f"added-center-limit={formula.added_center_limit} "
            f"residual-limit={formula.residual_limit}\n"
        )
        handle.write(
            "c primary-variable=base-3-word-value+1 "
            f"primary-variables={formula.primary_variable_count} "
            f"candidate-centers={len(formula.candidate_centers)}\n"
        )
        handle.write(f"c fixed-core={fixed_core}\n")
        handle.write(
            f"c core-holes={len(formula.core_holes)} "
            f"hole-slack-variables={slack_start}..{slack_end}\n"
        )
        handle.write(
            "c clause-counts "
            f"fixed-core-exclusions={counts.fixed_core_exclusions} "
            f"residual-covering={counts.residual_covering} "
            "added-center-cardinality="
            f"{counts.added_center_cardinality} "
            "uncovered-hole-cardinality="
            f"{counts.uncovered_hole_cardinality}\n"
        )
        handle.write(
            f"p cnf {formula.variable_count} {counts.total}\n"
        )
        for clause in formula.clauses:
            handle.write(" ".join(str(literal) for literal in clause))
            handle.write(" 0\n")
