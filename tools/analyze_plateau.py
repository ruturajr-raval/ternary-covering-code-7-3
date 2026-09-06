#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

from ternary_covering_code.plateau import (
    PlateauReport,
    analyze_plateau,
    report_to_dict,
)
from ternary_covering_code.space import Word
from ternary_covering_code.verify import load_code


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "search" / "plateau_classes.json"


def load_manifest(path: Path) -> Mapping[str, object]:
    return json.loads(path.read_text(encoding="ascii"))


def load_labeled_codes(
    manifest: Mapping[str, object],
    data_directory: Path,
) -> Dict[str, Sequence[Word]]:
    result: Dict[str, Sequence[Word]] = {}
    classes = manifest["classes"]
    if not isinstance(classes, dict):
        raise ValueError("Manifest classes must be an object.")
    for label, row in sorted(classes.items()):
        if not isinstance(row, dict):
            raise ValueError("Every manifest class must be an object.")
        source = data_directory / str(row["source"])
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != row["sha256"]:
            raise ValueError(f"Hash mismatch for {source.name}.")
        result[label] = load_code(source)
    return result


def validate_report(
    report: PlateauReport,
    manifest: Mapping[str, object],
) -> List[str]:
    actual = report_to_dict(report)
    expected = manifest["expected"]
    classes = manifest["classes"]
    if not isinstance(expected, dict) or not isinstance(classes, dict):
        raise ValueError("Manifest expected/classes sections must be objects.")
    errors: List[str] = []

    direct_keys = (
        "canonical_hole",
        "repair_center_count",
        "pair_isometry_class_count",
        "canonical_core",
        "plateau_neighbor_count",
        "adjacency",
    )
    for key in direct_keys:
        if actual[key] != expected[key]:
            errors.append(f"{key}: expected {expected[key]!r}, found {actual[key]!r}")

    core = actual["core_completion"]
    if not isinstance(core, dict):
        errors.append("core_completion is not an object")
    else:
        core_pairs = {
            "core_hole_count": "core_hole_count",
            "minimum_residual": "core_completion_minimum",
            "optimal_tail_count": "optimal_tail_count",
            "optimal_tails": "optimal_tails",
            "tail_class_count": "tail_stabilizer_class_count",
            "core_stabilizer_size": "core_stabilizer_size",
        }
        for actual_key, expected_key in core_pairs.items():
            if core[actual_key] != expected[expected_key]:
                errors.append(
                    f"core_completion.{actual_key}: expected "
                    f"{expected[expected_key]!r}, found {core[actual_key]!r}"
                )

    observed_tails = actual["observed_tails"]
    replacements = actual["replacements"]
    if not isinstance(observed_tails, dict) or not isinstance(replacements, dict):
        errors.append("observed_tails/replacements are not objects")
        return errors

    for label, row in sorted(classes.items()):
        if not isinstance(row, dict):
            errors.append(f"class {label} is not an object")
            continue
        if observed_tails[label] != row["canonical_tail"]:
            errors.append(f"class {label} canonical tail mismatch")
        replacement = replacements[label]
        if replacement["strict_one_minimum"] != expected["strict_one_minima"][label]:
            errors.append(f"class {label} strict one minimum mismatch")
        if replacement["strict_two_minimum"] != expected["strict_two_minima"][label]:
            errors.append(f"class {label} strict two minimum mismatch")
        if (
            replacement["plateau_neighbor_count"]
            != expected["plateau_neighbor_counts"][label]
        ):
            errors.append(f"class {label} plateau neighbor count mismatch")
        if (
            replacement["neighbor_class_counts"]
            != expected["neighbor_class_counts"][label]
        ):
            errors.append(f"class {label} neighbor class counts mismatch")
        if (
            replacement["raw_two_candidates"]
            != expected["raw_strict_two_candidates_per_class"]
        ):
            errors.append(f"class {label} raw pair count mismatch")
    raw_total = sum(
        replacements[label]["raw_two_candidates"]
        for label in replacements
    )
    if raw_total != expected["raw_strict_two_candidates_total"]:
        errors.append(
            "raw strict-two total: expected "
            f"{expected['raw_strict_two_candidates_total']!r}, "
            f"found {raw_total!r}"
        )
    return errors


def print_report(report: PlateauReport, elapsed: float) -> None:
    data = report_to_dict(report)
    core = data["core_completion"]
    replacements = data["replacements"]

    print("PROVED COMPUTATIONS - FINITE EXHAUSTIVE")
    print(f"canonical_hole={data['canonical_hole']}")
    print(f"common_repair_centers={data['repair_center_count']}")
    print(f"pair_isometry_classes={data['pair_isometry_class_count']}")
    print(f"canonical_core={data['canonical_core']}")
    print(f"core_holes={core['core_hole_count']}")
    print(f"core_completion_minimum={core['minimum_residual']}")
    print(f"optimal_tail_sets={core['optimal_tail_count']}")
    print(f"core_tail_stabilizer_classes={core['tail_class_count']}")
    print(f"core_stabilizer_size={core['core_stabilizer_size']}")
    for label in sorted(replacements):
        row = replacements[label]
        print(
            f"class={label} strict_one={row['strict_one_minimum']} "
            f"strict_two={row['strict_two_minimum']} "
            f"neighbors={row['plateau_neighbor_count']} "
            f"targets={row['neighbor_class_counts']}"
        )
    print(f"plateau_neighbors={data['plateau_neighbor_count']}")
    print(f"adjacency={data['adjacency']}")

    print()
    print("AUDIT COUNTS")
    print(f"core_raw_triples={core['raw_candidate_triples']}")
    print(f"core_decision_mask_pair_checks={core['decision_mask_pair_checks']}")
    print(
        "core_enumeration_mask_pair_checks="
        f"{core['enumeration_mask_pair_checks']}"
    )
    raw_pairs = sum(
        replacements[label]["raw_two_candidates"]
        for label in replacements
    )
    optimized_checks = sum(
        replacements[label]["optimization_mask_pair_checks"]
        for label in replacements
    )
    enumeration_checks = sum(
        replacements[label]["enumeration_mask_pair_checks"]
        for label in replacements
    )
    print(f"strict_two_raw_candidate_codes={raw_pairs}")
    print(f"strict_two_optimization_mask_pair_checks={optimized_checks}")
    print(f"strict_two_enumeration_mask_pair_checks={enumeration_checks}")

    print()
    print("CONJECTURE - NOT PROVED")
    print(
        "The four retained classes may be the complete balanced six-hole "
        "basin. No global classification of all size-11 near-covers is claimed."
    )
    print()
    print(f"elapsed_seconds={elapsed:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    codes = load_labeled_codes(manifest, args.manifest.parent)
    started = time.perf_counter()
    report = analyze_plateau(codes)
    elapsed = time.perf_counter() - started
    errors = validate_report(report, manifest)
    if errors:
        raise SystemExit("Plateau validation failed:\n" + "\n".join(errors))
    if args.json:
        payload = report_to_dict(report)
        payload["elapsed_seconds"] = round(elapsed, 6)
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_report(report, elapsed)


if __name__ == "__main__":
    main()
