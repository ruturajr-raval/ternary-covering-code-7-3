import os
import subprocess
import sys
import tempfile
import unittest
from itertools import combinations, product
from pathlib import Path

from ternary_covering_code.branch_cnf import (
    diameter_branch_formula,
    primary_variable,
)
from ternary_covering_code.branches import (
    branch_diameters,
    diameter_branch,
)
from ternary_covering_code.cnf import sequential_at_most
from ternary_covering_code.space import (
    Q,
    RADIUS,
    WORD_COUNT,
    all_words,
    ball,
    hamming_distance,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_K11 = {
    4: {
        "allowed": 453,
        "variables": 6237,
        "anchors": 2,
        "forbidden_centers": 1734,
        "incompatible_pairs": 38670,
        "covering": 2187,
        "cardinality": 8533,
        "total": 51126,
    },
    5: {
        "allowed": 1163,
        "variables": 12627,
        "anchors": 2,
        "forbidden_centers": 1024,
        "incompatible_pairs": 156000,
        "covering": 2187,
        "cardinality": 22023,
        "total": 181236,
    },
    6: {
        "allowed": 1933,
        "variables": 19557,
        "anchors": 2,
        "forbidden_centers": 254,
        "incompatible_pairs": 109038,
        "covering": 2187,
        "cardinality": 36653,
        "total": 148134,
    },
    7: {
        "allowed": 2187,
        "variables": 21843,
        "anchors": 2,
        "forbidden_centers": 0,
        "incompatible_pairs": 0,
        "covering": 2187,
        "cardinality": 41479,
        "total": 43668,
    },
}


def clause_ranges(formula):
    counts = formula.clause_counts
    start = 0
    result = {}
    for name in (
        "anchors",
        "forbidden_centers",
        "incompatible_pairs",
        "covering",
        "cardinality",
    ):
        end = start + getattr(counts, name)
        result[name] = formula.clauses[start:end]
        start = end
    if start != len(formula.clauses):
        raise AssertionError("Clause ranges do not consume the formula.")
    return result


def pairwise_clauses_hold(clauses, selected_variables):
    selected = frozenset(selected_variables)
    return all(
        not (
            abs(clause[0]) in selected
            and abs(clause[1]) in selected
        )
        for clause in clauses
    )


class DiameterBranchCNFCountTests(unittest.TestCase):
    def test_invalid_parameters_are_rejected(self):
        for invalid_diameter in (True, 4.0, 3, 8):
            expected_error = (
                TypeError
                if isinstance(invalid_diameter, (bool, float))
                else ValueError
            )
            with self.assertRaises(expected_error):
                diameter_branch_formula(invalid_diameter, limit=11)

        for invalid_limit in (True, 11.0, -1):
            expected_error = (
                TypeError
                if isinstance(invalid_limit, (bool, float))
                else ValueError
            )
            with self.assertRaises(expected_error):
                diameter_branch_formula(4, limit=invalid_limit)

    def test_k11_counts_are_deterministic(self):
        for diameter, expected in EXPECTED_K11.items():
            first = diameter_branch_formula(diameter, limit=11)
            second = diameter_branch_formula(diameter, limit=11)
            counts = first.clause_counts

            self.assertEqual(first, second)
            self.assertEqual(first.primary_variable_count, WORD_COUNT)
            self.assertEqual(
                len(first.allowed_center_variables),
                expected["allowed"],
            )
            self.assertEqual(first.variable_count, expected["variables"])
            self.assertEqual(counts.anchors, expected["anchors"])
            self.assertEqual(
                counts.forbidden_centers,
                expected["forbidden_centers"],
            )
            self.assertEqual(
                counts.incompatible_pairs,
                expected["incompatible_pairs"],
            )
            self.assertEqual(counts.covering, expected["covering"])
            self.assertEqual(
                counts.cardinality,
                expected["cardinality"],
            )
            self.assertEqual(counts.total, expected["total"])
            self.assertEqual(len(first.clauses), expected["total"])

    def test_cardinality_counter_reserves_both_anchor_slots(self):
        for diameter in branch_diameters():
            formula = diameter_branch_formula(diameter, limit=11)
            groups = clause_ranges(formula)
            self.assertEqual(formula.cardinality_limit, 9)
            self.assertEqual(
                len(formula.cardinality_variables),
                len(formula.allowed_center_variables) - 2,
            )
            self.assertTrue(
                set(formula.anchor_variables).isdisjoint(
                    formula.cardinality_variables
                )
            )

            expected, next_variable, _ = sequential_at_most(
                formula.cardinality_variables,
                limit=9,
                next_variable=WORD_COUNT + 1,
            )
            self.assertEqual(
                groups["cardinality"],
                tuple(tuple(clause) for clause in expected),
            )
            self.assertEqual(formula.variable_count, next_variable - 1)

    def test_limit_below_two_is_explicitly_unsatisfiable(self):
        for limit in (0, 1):
            formula = diameter_branch_formula(4, limit=limit)
            groups = clause_ranges(formula)
            self.assertIn((), groups["cardinality"])


class DiameterBranchCNFSemanticTests(unittest.TestCase):
    def test_anchor_and_forbidden_center_units_are_exact(self):
        all_variables = frozenset(range(1, WORD_COUNT + 1))
        for diameter in branch_diameters():
            branch = diameter_branch(diameter)
            formula = diameter_branch_formula(diameter, limit=11)
            groups = clause_ranges(formula)
            allowed = frozenset(formula.allowed_center_variables)

            self.assertEqual(
                groups["anchors"],
                tuple(
                    (primary_variable(anchor),)
                    for anchor in branch.anchors
                ),
            )
            self.assertEqual(
                groups["forbidden_centers"],
                tuple(
                    (-variable,)
                    for variable in sorted(all_variables - allowed)
                ),
            )

    def test_every_allowed_pair_has_exact_diameter_semantics(self):
        for diameter in branch_diameters():
            branch = diameter_branch(diameter)
            formula = diameter_branch_formula(diameter, limit=11)
            pair_clauses = frozenset(
                clause_ranges(formula)["incompatible_pairs"]
            )

            checked_pairs = 0
            for left, right in combinations(branch.allowed_centers, 2):
                clause = (
                    -primary_variable(left),
                    -primary_variable(right),
                )
                self.assertEqual(
                    clause in pair_clauses,
                    hamming_distance(left, right) > diameter,
                )
                checked_pairs += 1
            self.assertEqual(
                checked_pairs,
                len(branch.allowed_centers)
                * (len(branch.allowed_centers) - 1)
                // 2,
            )

    def test_small_assignments_match_pairwise_admissibility(self):
        branch = diameter_branch(4)
        formula = diameter_branch_formula(4, limit=11)
        pair_clauses = clause_ranges(formula)["incompatible_pairs"]
        incompatible = next(
            (left, right)
            for left, right in combinations(branch.allowed_centers, 2)
            if hamming_distance(left, right) > branch.diameter
        )
        candidates = tuple(
            dict.fromkeys(branch.anchors + incompatible)
        )
        candidate_variables = tuple(
            primary_variable(center) for center in candidates
        )

        for values in product((False, True), repeat=len(candidates)):
            if not all(values[index] for index in range(2)):
                continue
            selected_centers = tuple(
                center
                for center, selected in zip(candidates, values)
                if selected
            )
            selected_variables = tuple(
                variable
                for variable, selected in zip(candidate_variables, values)
                if selected
            )
            self.assertEqual(
                pairwise_clauses_hold(pair_clauses, selected_variables),
                branch.code_is_admissible(selected_centers),
            )

    def test_covering_clause_for_every_target_is_exact(self):
        words = all_words()
        for diameter in branch_diameters():
            formula = diameter_branch_formula(diameter, limit=11)
            groups = clause_ranges(formula)
            allowed = frozenset(diameter_branch(diameter).allowed_centers)
            self.assertEqual(len(groups["covering"]), WORD_COUNT)

            for target, clause in zip(words, groups["covering"]):
                expected = tuple(
                    sorted(
                        primary_variable(center)
                        for center in ball(
                            target,
                            radius=RADIUS,
                            q=Q,
                        )
                        if center in allowed
                    )
                )
                self.assertEqual(clause, expected)


class DiameterBranchCNFCLITests(unittest.TestCase):
    def test_cli_writes_deterministic_dimacs(self):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".branch-cnf-test-",
        ) as temporary_directory:
            first = Path(temporary_directory) / "first.cnf"
            second = Path(temporary_directory) / "second.cnf"
            base_command = [
                sys.executable,
                str(ROOT / "tools" / "generate_branch_cnf.py"),
                "--diameter",
                "4",
                "--limit",
                "11",
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
            self.assertIn(
                "diameter=4 limit=11 variables=6237 clauses=51126",
                first_result.stdout,
            )
            self.assertIn(
                "diameter=4 limit=11 variables=6237 clauses=51126",
                second_result.stdout,
            )
            self.assertEqual(rendered[4], "p cnf 6237 51126")
            self.assertEqual(len(rendered), 5 + 51126)


if __name__ == "__main__":
    unittest.main()
