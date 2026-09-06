import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ternary_covering_code.cnf import sequential_at_most
from ternary_covering_code.core_completion_cnf import (
    ADDED_CENTER_LIMIT,
    FIXED_CORE,
    core_completion_formula,
    extract_core_completion_model,
    primary_variable,
)
from ternary_covering_code.space import (
    Q,
    RADIUS,
    WORD_COUNT,
    all_words,
    ball,
    hamming_distance,
    parse_word,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    5: {
        "variables": 10234,
        "fixed_core_exclusions": 8,
        "residual_covering": 253,
        "added_center_cardinality": 15241,
        "uncovered_hole_cardinality": 2763,
        "total": 18265,
    },
    6: {
        "variables": 10486,
        "fixed_core_exclusions": 8,
        "residual_covering": 253,
        "added_center_cardinality": 15241,
        "uncovered_hole_cardinality": 3265,
        "total": 18767,
    },
}
KNOWN_TAIL = tuple(
    parse_word(text)
    for text in (
        "1112212",
        "2220121",
        "2221212",
    )
)
EXPECTED_UNCOVERED = tuple(
    parse_word(text)
    for text in (
        "0011000",
        "0101000",
        "0110000",
        "1001000",
        "1010000",
        "1100000",
    )
)


def clause_ranges(formula):
    counts = formula.clause_counts
    start = 0
    result = {}
    for name in (
        "fixed_core_exclusions",
        "residual_covering",
        "added_center_cardinality",
        "uncovered_hole_cardinality",
    ):
        end = start + getattr(counts, name)
        result[name] = formula.clauses[start:end]
        start = end
    if start != len(formula.clauses):
        raise AssertionError("Clause ranges do not consume the formula.")
    return result


def counter_witness(input_variables, counter_metadata, true_variables):
    true_set = frozenset(true_variables)
    witness = {}
    prefix_counts = [0]
    for variable in input_variables:
        prefix_counts.append(
            prefix_counts[-1] + int(variable in true_set)
        )
    for row, column, variable in counter_metadata:
        witness[variable] = prefix_counts[row] >= column
    return witness


def full_assignment(formula, selected_centers, uncovered_holes):
    assignment = {
        variable: False
        for variable in range(1, formula.variable_count + 1)
    }
    selected_variables = tuple(
        primary_variable(center) for center in selected_centers
    )
    hole_to_variable = dict(
        zip(formula.core_holes, formula.hole_slack_variables)
    )
    uncovered_variables = tuple(
        hole_to_variable[hole] for hole in uncovered_holes
    )
    for variable in selected_variables + uncovered_variables:
        assignment[variable] = True
    assignment.update(
        counter_witness(
            formula.candidate_center_variables,
            formula.added_center_counter_variables,
            selected_variables,
        )
    )
    assignment.update(
        counter_witness(
            formula.hole_slack_variables,
            formula.uncovered_hole_counter_variables,
            uncovered_variables,
        )
    )
    return assignment


def clause_holds(clause, assignment):
    return any(
        assignment[abs(literal)] == (literal > 0)
        for literal in clause
    )


class CoreCompletionCNFMetadataTests(unittest.TestCase):
    def test_invalid_residual_limits_are_rejected(self):
        for invalid_limit in (True, 5.0, -1):
            expected_error = (
                TypeError
                if isinstance(invalid_limit, (bool, float))
                else ValueError
            )
            with self.assertRaises(expected_error):
                core_completion_formula(invalid_limit)

    def test_fixed_core_and_residual_space_are_recomputed(self):
        formula = core_completion_formula(5)
        words = all_words()
        fixed_core_set = frozenset(FIXED_CORE)

        self.assertEqual(
            tuple("".join(map(str, word)) for word in FIXED_CORE),
            (
                "0000011",
                "0000102",
                "0000220",
                "0002121",
                "1111022",
                "1111110",
                "1111201",
                "2222000",
            ),
        )
        self.assertEqual(len(formula.fixed_core), 8)
        self.assertEqual(len(formula.core_holes), 253)
        self.assertEqual(len(formula.candidate_centers), 2179)
        self.assertEqual(
            formula.candidate_centers,
            tuple(word for word in words if word not in fixed_core_set),
        )
        self.assertEqual(
            formula.core_holes,
            tuple(
                target
                for target in words
                if all(
                    hamming_distance(target, center) > RADIUS
                    for center in FIXED_CORE
                )
            ),
        )
        self.assertTrue(
            all(
                all(
                    hamming_distance(target, center) > RADIUS
                    for center in FIXED_CORE
                )
                for target in formula.core_holes
            )
        )

    def test_r5_and_r6_counts_are_exact_and_deterministic(self):
        for residual_limit, expected in EXPECTED.items():
            first = core_completion_formula(residual_limit)
            second = core_completion_formula(residual_limit)
            counts = first.clause_counts

            self.assertEqual(first, second)
            self.assertEqual(first.residual_limit, residual_limit)
            self.assertEqual(
                first.added_center_limit,
                ADDED_CENTER_LIMIT,
            )
            self.assertEqual(first.primary_variable_count, WORD_COUNT)
            self.assertEqual(first.variable_count, expected["variables"])
            self.assertEqual(
                counts.fixed_core_exclusions,
                expected["fixed_core_exclusions"],
            )
            self.assertEqual(
                counts.residual_covering,
                expected["residual_covering"],
            )
            self.assertEqual(
                counts.added_center_cardinality,
                expected["added_center_cardinality"],
            )
            self.assertEqual(
                counts.uncovered_hole_cardinality,
                expected["uncovered_hole_cardinality"],
            )
            self.assertEqual(counts.total, expected["total"])
            self.assertEqual(len(first.clauses), expected["total"])
            self.assertEqual(
                first.hole_slack_variables,
                tuple(range(2188, 2441)),
            )


class CoreCompletionCNFSemanticTests(unittest.TestCase):
    def test_fixed_core_exclusions_and_covering_clauses_are_exact(self):
        formula = core_completion_formula(5)
        groups = clause_ranges(formula)
        fixed_core_set = frozenset(FIXED_CORE)

        self.assertEqual(
            groups["fixed_core_exclusions"],
            tuple(
                (-primary_variable(center),)
                for center in FIXED_CORE
            ),
        )
        self.assertEqual(len(groups["residual_covering"]), 253)
        for target, slack_variable, clause in zip(
            formula.core_holes,
            formula.hole_slack_variables,
            groups["residual_covering"],
        ):
            expected_coverers = tuple(
                sorted(
                    primary_variable(center)
                    for center in ball(
                        target,
                        radius=RADIUS,
                        q=Q,
                    )
                    if center not in fixed_core_set
                )
            )
            self.assertEqual(clause, (slack_variable,) + expected_coverers)
            self.assertEqual(len(expected_coverers), 379)

    def test_both_cardinality_encodings_are_exact(self):
        for residual_limit in EXPECTED:
            formula = core_completion_formula(residual_limit)
            groups = clause_ranges(formula)
            first_auxiliary = formula.hole_slack_variables[-1] + 1
            added_clauses, next_variable, added_counter = (
                sequential_at_most(
                    formula.candidate_center_variables,
                    ADDED_CENTER_LIMIT,
                    first_auxiliary,
                )
            )
            hole_clauses, final_variable, hole_counter = (
                sequential_at_most(
                    formula.hole_slack_variables,
                    residual_limit,
                    next_variable,
                )
            )

            self.assertEqual(
                groups["added_center_cardinality"],
                tuple(tuple(clause) for clause in added_clauses),
            )
            self.assertEqual(
                groups["uncovered_hole_cardinality"],
                tuple(tuple(clause) for clause in hole_clauses),
            )
            self.assertEqual(
                formula.added_center_counter_variables,
                tuple(
                    (row, column, variable)
                    for (row, column), variable
                    in sorted(added_counter.items())
                ),
            )
            self.assertEqual(
                formula.uncovered_hole_counter_variables,
                tuple(
                    (row, column, variable)
                    for (row, column), variable
                    in sorted(hole_counter.items())
                ),
            )
            self.assertEqual(formula.variable_count, final_variable - 1)

    def test_known_tail_is_a_complete_r6_sat_witness(self):
        formula = core_completion_formula(6)
        uncovered = tuple(
            target
            for target in formula.core_holes
            if all(
                hamming_distance(target, center) > RADIUS
                for center in KNOWN_TAIL
            )
        )
        self.assertEqual(uncovered, EXPECTED_UNCOVERED)
        self.assertEqual(len(uncovered), 6)

        assignment = full_assignment(
            formula,
            selected_centers=KNOWN_TAIL,
            uncovered_holes=uncovered,
        )
        self.assertTrue(
            all(
                clause_holds(clause, assignment)
                for clause in formula.clauses
            )
        )

        model_literals = tuple(
            variable
            for variable, value in assignment.items()
            if value
        )
        extracted = extract_core_completion_model(
            formula,
            model_literals,
        )
        self.assertEqual(extracted.added_centers, KNOWN_TAIL)
        self.assertEqual(
            extracted.uncovered_core_holes,
            EXPECTED_UNCOVERED,
        )

    def test_known_tail_requires_six_slacks(self):
        formula = core_completion_formula(5)
        groups = clause_ranges(formula)
        selected = frozenset(
            primary_variable(center) for center in KNOWN_TAIL
        )
        required_slacks = tuple(
            clause[0]
            for clause in groups["residual_covering"]
            if selected.isdisjoint(clause[1:])
        )

        self.assertEqual(len(required_slacks), 6)
        required_holes = tuple(
            hole
            for hole, slack in zip(
                formula.core_holes,
                formula.hole_slack_variables,
            )
            if slack in required_slacks
        )
        self.assertEqual(required_holes, EXPECTED_UNCOVERED)


class CoreCompletionCNFCLITests(unittest.TestCase):
    def test_cli_writes_deterministic_dimacs(self):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".core-completion-cnf-test-",
        ) as temporary_directory:
            first = Path(temporary_directory) / "first.cnf"
            second = Path(temporary_directory) / "second.cnf"
            base_command = [
                sys.executable,
                str(
                    ROOT
                    / "tools"
                    / "generate_core_completion_cnf.py"
                ),
                "--residual-limit",
                "5",
            ]
            first_result = subprocess.run(
                base_command + ["--output", str(first)],
                cwd=ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            second_result = subprocess.run(
                base_command + ["--output", str(second)],
                cwd=ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(first.read_bytes(), second.read_bytes())
            rendered = first.read_text(encoding="ascii").splitlines()
            expected_summary = (
                "fixed-core-size=8 core-holes=253 "
                "candidate-centers=2179 added-center-limit=3 "
                "residual-limit=5 variables=10234 clauses=18265"
            )
            self.assertIn(expected_summary, first_result.stdout)
            self.assertIn(expected_summary, second_result.stdout)
            self.assertEqual(rendered[5], "p cnf 10234 18265")
            self.assertEqual(len(rendered), 6 + 18265)


if __name__ == "__main__":
    unittest.main()
