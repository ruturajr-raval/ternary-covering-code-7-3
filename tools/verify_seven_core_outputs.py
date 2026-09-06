#!/usr/bin/env python3

"""Compare seven-core verifier output with the checked evidence record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "evidence" / "seven-core-results.json"


def parse_key_value_output(
    text: str,
) -> Tuple[Dict[str, str], List[Dict[str, str]], Dict[str, str]]:
    header: Dict[str, str] = {}
    reports: List[Dict[str, str]] = []
    conclusion: Dict[str, str] = {}
    current = header
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "VERIFIED CONCLUSION":
            current = conclusion
            continue
        if line.startswith("representative="):
            current = {}
            reports.append(current)
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        current[key] = value
    return header, reports, conclusion


def require_equal(
    errors: List[str],
    source: Path,
    label: str,
    actual: object,
    expected: object,
) -> None:
    if actual != expected:
        errors.append(
            f"{source}: {label}: expected {expected!r}, found {actual!r}"
        )


def normalized_hash(value: str) -> str:
    return value.removeprefix("0x").lower()


def validate_output(
    source: Path,
    evidence: Dict[str, object],
) -> Tuple[str, ...]:
    header, reports, conclusion = parse_key_value_output(
        source.read_text(encoding="ascii")
    )
    errors: List[str] = []
    expected_representatives = evidence["representatives"]
    expected_by_word = {
        row["deleted_word"]: row for row in expected_representatives
    }

    require_equal(
        errors,
        source,
        "ambient_words",
        int(header["ambient_words"]),
        evidence["space"]["ambient_words"],
    )
    require_equal(
        errors,
        source,
        "ball_size",
        int(header["ball_size"]),
        evidence["space"]["ball_size"],
    )
    require_equal(
        errors,
        source,
        "core",
        header["core"].split(","),
        evidence["core"],
    )
    stabilizer = header.get(
        "core_stabilizer",
        header.get("core_stabilizer_maps"),
    )
    require_equal(
        errors,
        source,
        "core stabilizer",
        int(stabilizer),
        evidence["symmetry"]["core_stabilizer_order"],
    )
    require_equal(
        errors,
        source,
        "deletion orbit count",
        int(header["deletion_orbit_count"]),
        len(evidence["symmetry"]["deletion_orbit_sizes"]),
    )

    require_equal(
        errors,
        source,
        "representative count",
        len(reports),
        len(expected_representatives),
    )
    for report in reports:
        representative = report["representative"]
        if representative not in expected_by_word:
            errors.append(f"{source}: unexpected representative {representative}")
            continue
        expected = expected_by_word[representative]
        threshold = report.get(
            "first_pair_threshold",
            report.get("first_pair_averaging_threshold"),
        )
        drift_hash = report.get(
            "first_pair_drift_hash_fnv64",
            report.get("eligible_first_pair_checksum"),
        )
        comparisons = (
            ("orbit_size", int(report["orbit_size"]), len(expected["orbit_members"])),
            (
                "orbit_members",
                report["orbit_members"].split(","),
                expected["orbit_members"],
            ),
            (
                "seven_core_holes",
                int(report["seven_core_holes"]),
                expected["initial_holes"],
            ),
            (
                "candidate_centers",
                int(report["candidate_centers"]),
                expected["candidate_centers"],
            ),
            (
                "unordered_candidate_pairs",
                int(report["unordered_candidate_pairs"]),
                expected["unordered_candidate_pairs"],
            ),
            (
                "first_pair_threshold",
                int(threshold),
                expected["first_pair_threshold"],
            ),
            (
                "eligible_first_pairs",
                int(report["eligible_first_pairs"]),
                expected["eligible_first_pairs"],
            ),
            (
                "queried_first_pairs",
                int(report.get("queried_first_pairs", "-1")),
                expected["eligible_first_pairs"],
            ),
            (
                "first_pair_drift_hash",
                normalized_hash(drift_hash),
                expected["first_pair_drift_hash_fnv64"],
            ),
            (
                "minimum_residual",
                int(report["minimum_residual"]),
                expected["minimum_residual"],
            ),
            (
                "witness_additions",
                report["witness_additions"].split(","),
                expected["witness_additions"],
            ),
            (
                "witness_holes",
                report["witness_holes"].split(","),
                evidence["witness_holes"],
            ),
            (
                "residual-at-most-5 completion",
                report["completion_with_residual_at_most_5"],
                "none",
            ),
        )
        for label, actual, expected_value in comparisons:
            require_equal(errors, source, label, actual, expected_value)

    require_equal(
        errors,
        source,
        "total pair entries",
        sum(int(report["unordered_candidate_pairs"]) for report in reports),
        evidence["totals"]["pair_entries_built"],
    )
    require_equal(
        errors,
        source,
        "total eligible first pairs",
        sum(int(report["eligible_first_pairs"]) for report in reports),
        evidence["totals"]["eligible_first_pairs_queried"],
    )

    if "deletion_orbit_sizes" in header:
        require_equal(
            errors,
            source,
            "deletion orbit sizes",
            [int(value) for value in header["deletion_orbit_sizes"].split(",")],
            evidence["symmetry"]["deletion_orbit_sizes"],
        )
    if "deletion_orbit_coverage" in header:
        require_equal(
            errors,
            source,
            "deletion orbit coverage",
            int(header["deletion_orbit_coverage"]),
            evidence["symmetry"]["deletions_covered"],
        )
    required_conclusion = {
        "representatives_verified": len(expected_representatives),
        "deletions_covered_by_orbits": evidence["symmetry"][
            "deletions_covered"
        ],
        "total_pair_entries_built": evidence["totals"]["pair_entries_built"],
        "total_eligible_first_pairs_queried": evidence["totals"][
            "eligible_first_pairs_queried"
        ],
        "all_four_representative_minima": evidence["theorem"][
            "minimum_residual"
        ],
    }
    for key, expected_value in required_conclusion.items():
        actual_text = conclusion.get(key)
        actual = int(actual_text) if actual_text is not None else None
        require_equal(
            errors,
            source,
            f"conclusion {key}",
            actual,
            expected_value,
        )
    require_equal(
        errors,
        source,
        "conclusion scope",
        conclusion.get("scope"),
        "the_eight_seven_word_subcores_and_their_isometric_copies",
    )
    if "self_tests" in header:
        controls = evidence["controls"]["cpp20"]
        require_equal(
            errors,
            source,
            "C++ self tests",
            header["self_tests"],
            "passed",
        )
        require_equal(
            errors,
            source,
            "C++ self-test pair queries",
            int(header.get("self_test_pair_queries", "-1")),
            controls["pair_queries"],
        )
        require_equal(
            errors,
            source,
            "C++ self-test four-center sets",
            int(header.get("self_test_four_sets", "-1")),
            controls["four_center_sets"],
        )
        require_equal(
            errors,
            source,
            "C++ self-test minimum",
            int(header.get("self_test_four_center_minimum", "-1")),
            controls["four_center_minimum"],
        )
    return tuple(errors)


def validate_all(
    sources: Iterable[Path],
    evidence_path: Path,
) -> Tuple[str, ...]:
    evidence = json.loads(evidence_path.read_text(encoding="ascii"))
    errors = []
    for source in sources:
        errors.extend(validate_output(source, evidence))
    return tuple(errors)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence",
        type=Path,
        default=DEFAULT_EVIDENCE,
    )
    parser.add_argument(
        "outputs",
        nargs="+",
        type=Path,
        help="Rust or C++ verifier output files",
    )
    args = parser.parse_args()
    errors = validate_all(args.outputs, args.evidence)
    if errors:
        raise SystemExit(
            "Seven-core output verification failed:\n" + "\n".join(errors)
        )
    print(
        f"evidence={args.evidence} outputs={len(args.outputs)} status=verified"
    )


if __name__ == "__main__":
    main()
