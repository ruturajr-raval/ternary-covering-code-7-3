import hashlib
import json
import unittest
from itertools import combinations, product
from pathlib import Path

from ternary_covering_code.plateau import (
    PlateauInvariantError,
    _apply_stabilizer,
    _best_pair_residual,
    _find_three_at_most,
    _pairs_at_residual,
    analyze_plateau,
    canonical_j42_hole,
    canonicalize_pair,
    code_ids,
    hamming_index,
    j42_stabilizer,
    report_to_dict,
    uncovered_count,
)
from ternary_covering_code.space import parse_word
from ternary_covering_code.verify import load_code


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "search" / "plateau_classes.json"


def count_bits(value):
    return bin(value).count("1")


class PlateauTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="ascii"))
        cls.codes = {}
        for label, row in sorted(cls.manifest["classes"].items()):
            path = MANIFEST_PATH.parent / row["source"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != row["sha256"]:
                raise AssertionError(f"Hash mismatch for {path.name}.")
            cls.codes[label] = load_code(path)
        cls.report = analyze_plateau(cls.codes)
        cls.actual = report_to_dict(cls.report)
        cls.expected = cls.manifest["expected"]

    def test_j42_hole_and_repair_centers(self):
        self.assertEqual(
            self.actual["canonical_hole"],
            self.expected["canonical_hole"],
        )
        self.assertEqual(self.actual["repair_center_count"], 30)
        self.assertEqual(self.actual["pair_isometry_class_count"], 4)

    def test_canonical_core_and_four_tails(self):
        self.assertEqual(
            self.actual["canonical_core"],
            self.expected["canonical_core"],
        )
        for label, row in self.manifest["classes"].items():
            self.assertEqual(
                self.actual["observed_tails"][label],
                row["canonical_tail"],
            )
        forms = self.actual["canonical_forms"]
        self.assertEqual(len({tuple(form) for form in forms.values()}), 4)

    def test_exact_core_completion(self):
        result = self.actual["core_completion"]
        self.assertEqual(result["core_hole_count"], 253)
        self.assertEqual(result["minimum_residual"], 6)
        self.assertEqual(result["optimal_tail_count"], 8)
        self.assertEqual(result["optimal_tails"], self.expected["optimal_tails"])
        self.assertEqual(result["tail_class_count"], 4)
        self.assertEqual(result["core_stabilizer_size"], 18)
        self.assertGreater(result["raw_candidate_triples"], 1_000_000_000)
        self.assertLess(
            result["enumeration_mask_pair_checks"],
            result["raw_candidate_triples"],
        )

    def test_exact_replacement_plateau(self):
        raw_total = 0
        for label, result in self.actual["replacements"].items():
            self.assertEqual(
                result["strict_one_minimum"],
                self.expected["strict_one_minima"][label],
            )
            self.assertEqual(result["strict_two_minimum"], 6)
            self.assertEqual(
                result["plateau_neighbor_count"],
                self.expected["plateau_neighbor_counts"][label],
            )
            self.assertEqual(
                result["neighbor_class_counts"],
                self.expected["neighbor_class_counts"][label],
            )
            self.assertLess(
                result["optimization_mask_pair_checks"],
                result["raw_two_candidates"],
            )
            raw_total += result["raw_two_candidates"]
        self.assertEqual(raw_total, 520_608_000)
        self.assertEqual(self.actual["plateau_neighbor_count"], 30)
        self.assertEqual(self.actual["adjacency"], self.expected["adjacency"])

    def test_positive_mutation_controls(self):
        index = hamming_index()

        source = list(code_ids(self.codes["A"]))
        source[-1] = parse_word("2212011")
        mutant = code_ids(
            index.words[center] if isinstance(center, int) else center
            for center in source
        )
        with self.assertRaises(PlateauInvariantError):
            canonicalize_pair(mutant, index)

        core = tuple(parse_word(word) for word in self.expected["canonical_core"])
        tail = [
            parse_word(word)
            for word in self.manifest["classes"]["A"]["canonical_tail"]
        ]
        optimum = code_ids(core + tuple(tail))
        self.assertEqual(uncovered_count(optimum, index), 6)
        tail[0] = parse_word("1112211")
        changed = code_ids(core + tuple(tail))
        self.assertNotEqual(uncovered_count(changed, index), 6)

        class_a = dict(self.report.replacements)["A"]
        self.assertTrue(class_a.plateau_neighbors)
        neighbor = class_a.plateau_neighbors[0]
        self.assertNotEqual(neighbor, code_ids(self.codes["A"]))
        self.assertEqual(uncovered_count(neighbor, index), 6)

    def test_pair_mask_pruning_matches_exhaustive_small_universe(self):
        hole_mask = 0b1111
        allowed = tuple(range(4))
        for masks in product(range(16), repeat=4):
            expected_rows = tuple(
                (
                    (first, second),
                    count_bits(
                        hole_mask & ~(masks[first] | masks[second])
                    ),
                )
                for first, second in combinations(allowed, 2)
            )
            expected_minimum = min(residual for _, residual in expected_rows)
            actual_minimum, _, _ = _best_pair_residual(
                hole_mask,
                allowed,
                masks,
            )
            actual_pairs, _, _ = _pairs_at_residual(
                hole_mask,
                allowed,
                masks,
                expected_minimum,
            )
            expected_pairs = tuple(
                pair
                for pair, residual in expected_rows
                if residual == expected_minimum
            )
            self.assertEqual(actual_minimum, expected_minimum)
            self.assertEqual(actual_pairs, expected_pairs)

    def test_three_center_decision_matches_exhaustive_controls(self):
        hole_mask = 0b11111
        allowed = tuple(range(5))
        samples = (
            (0, 0, 0, 0, 0),
            (31, 0, 0, 0, 0),
            (1, 2, 4, 8, 16),
            (3, 6, 12, 24, 17),
            (7, 25, 10, 20, 5),
            (15, 23, 27, 29, 30),
        )
        for masks in samples:
            for residual_limit in range(6):
                expected = any(
                    count_bits(
                        hole_mask
                        & ~(masks[first] | masks[second] | masks[third])
                    )
                    <= residual_limit
                    for first, second, third in combinations(allowed, 3)
                )
                witness, _, _ = _find_three_at_most(
                    hole_mask,
                    allowed,
                    masks,
                    residual_limit,
                )
                self.assertEqual(witness is not None, expected)
                if witness is not None:
                    self.assertEqual(len(set(witness)), 3)
                    self.assertLessEqual(
                        count_bits(
                            hole_mask
                            & ~(
                                masks[witness[0]]
                                | masks[witness[1]]
                                | masks[witness[2]]
                            )
                        ),
                        residual_limit,
                    )

    def test_declared_j42_stabilizer_is_exact(self):
        hole = frozenset(canonical_j42_hole())
        stabilizer = j42_stabilizer()
        self.assertEqual(len(stabilizer), 2304)
        self.assertEqual(len(set(stabilizer)), 2304)
        for transform in stabilizer:
            image = frozenset(
                _apply_stabilizer(word, transform)
                for word in hole
            )
            self.assertEqual(image, hole)


if __name__ == "__main__":
    unittest.main()
