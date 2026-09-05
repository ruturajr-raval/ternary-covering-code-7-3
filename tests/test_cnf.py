import itertools
import unittest

from ternary_covering_code.cnf import sequential_at_most


def clause_value(clause, assignment):
    return any(
        assignment[abs(literal)] == (literal > 0)
        for literal in clause
    )


def has_auxiliary_witness(clauses, primary, first_auxiliary, last_variable):
    auxiliaries = range(first_auxiliary, last_variable + 1)
    for values in itertools.product((False, True), repeat=len(auxiliaries)):
        assignment = dict(primary)
        assignment.update(dict(zip(auxiliaries, values)))
        if all(clause_value(clause, assignment) for clause in clauses):
            return True
    return False


class CardinalityTests(unittest.TestCase):
    def test_small_sequential_counter_exhaustively(self):
        variables = list(range(1, 6))
        clauses, next_variable, _ = sequential_at_most(
            variables,
            limit=2,
            next_variable=6,
        )
        for values in itertools.product((False, True), repeat=len(variables)):
            primary = dict(zip(variables, values))
            satisfiable = has_auxiliary_witness(
                clauses,
                primary,
                first_auxiliary=6,
                last_variable=next_variable - 1,
            )
            self.assertEqual(satisfiable, sum(values) <= 2)


if __name__ == "__main__":
    unittest.main()
