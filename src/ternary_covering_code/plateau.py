"""Exact analysis of the retained six-hole size-11 plateau.

The routines in this module perform finite exhaustive computations. They do
not infer a global value for K_3(7,3). Candidate centers with identical
coverage on a current finite hole set are grouped into one exact mask class,
which avoids enumerating hundreds of millions of equivalent center pairs.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, permutations, product
from math import comb
from typing import (
    DefaultDict,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from .space import N, Q, RADIUS, WORD_COUNT, Word, all_words, ball, encode


Transform = Tuple[
    Tuple[int, ...],
    Tuple[int, ...],
    int,
    Tuple[int, ...],
]


class PlateauInvariantError(ValueError):
    """Raised when retained data violates a required finite invariant."""


def _popcount(value: int) -> int:
    method = getattr(int, "bit_count", None)
    if method is not None:
        return method(value)
    return bin(value).count("1")


def _iter_bits(mask: int) -> Iterator[int]:
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


def word_text(word: Sequence[int]) -> str:
    return "".join(str(symbol) for symbol in word)


@dataclass(frozen=True)
class HammingIndex:
    words: Tuple[Word, ...]
    ball_points: Tuple[Tuple[int, ...], ...]
    ball_masks: Tuple[int, ...]
    full_mask: int


@lru_cache(maxsize=1)
def hamming_index() -> HammingIndex:
    words = all_words()
    point_rows: List[Tuple[int, ...]] = []
    masks: List[int] = []
    for center in words:
        points = tuple(sorted(encode(point) for point in ball(center)))
        if len(points) != 379 or len(set(points)) != 379:
            raise PlateauInvariantError("A radius-3 ball does not have 379 points.")
        mask = 0
        for point in points:
            mask |= 1 << point
        point_rows.append(points)
        masks.append(mask)
    return HammingIndex(
        words=words,
        ball_points=tuple(point_rows),
        ball_masks=tuple(masks),
        full_mask=(1 << WORD_COUNT) - 1,
    )


def code_ids(code: Iterable[Word]) -> Tuple[int, ...]:
    result = tuple(sorted(encode(word) for word in code))
    if len(result) != len(set(result)):
        raise PlateauInvariantError("A code contains duplicate centers.")
    return result


def uncovered_mask(
    centers: Iterable[int],
    index: Optional[HammingIndex] = None,
) -> int:
    space = index or hamming_index()
    covered = 0
    for center in centers:
        covered |= space.ball_masks[center]
    return space.full_mask & ~covered


def uncovered_count(
    centers: Iterable[int],
    index: Optional[HammingIndex] = None,
) -> int:
    return _popcount(uncovered_mask(centers, index))


@lru_cache(maxsize=1)
def canonical_j42_hole() -> Tuple[Word, ...]:
    words: List[Word] = []
    for support in combinations(range(4), 2):
        word = [0] * N
        for coordinate in support:
            word[coordinate] = 1
        words.append(tuple(word))
    return tuple(sorted(words))


@lru_cache(maxsize=1)
def j42_stabilizer() -> Tuple[Transform, ...]:
    transforms: List[Transform] = []
    for active_permutation in permutations(range(4)):
        for inactive_permutation in permutations(range(3)):
            for complement in (0, 1):
                for inactive_swaps in product((0, 1), repeat=3):
                    transforms.append(
                        (
                            active_permutation,
                            inactive_permutation,
                            complement,
                            inactive_swaps,
                        )
                    )
    if len(transforms) != 2304:
        raise PlateauInvariantError("The J(4,2) stabilizer has the wrong size.")
    return tuple(transforms)


def _apply_stabilizer(word: Word, transform: Transform) -> Word:
    active_permutation, inactive_permutation, complement, swaps = transform
    output: List[int] = []
    for coordinate in active_permutation:
        symbol = word[coordinate]
        if complement and symbol in (0, 1):
            symbol = 1 - symbol
        output.append(symbol)
    for output_coordinate, coordinate in enumerate(inactive_permutation):
        symbol = word[4 + coordinate]
        if swaps[output_coordinate] and symbol in (1, 2):
            symbol = 3 - symbol
        output.append(symbol)
    return tuple(output)


def _normalize_pair(
    centers: Sequence[int],
    hole_ids: Sequence[int],
    index: HammingIndex,
) -> Tuple[Word, ...]:
    if len(hole_ids) != 6:
        raise PlateauInvariantError("Canonical plateau analysis requires six holes.")

    holes = tuple(index.words[point] for point in hole_ids)
    active: List[int] = []
    inactive: List[int] = []
    for coordinate in range(N):
        symbols = {word[coordinate] for word in holes}
        if len(symbols) == 2:
            active.append(coordinate)
        elif len(symbols) == 1:
            inactive.append(coordinate)
        else:
            raise PlateauInvariantError("The hole is not an embedded binary slice.")
    if len(active) != 4 or len(inactive) != 3:
        raise PlateauInvariantError("The hole is not an embedded J(4,2).")

    expected_hole = set(canonical_j42_hole())
    ordered_coordinates = active + inactive
    for flips in product((0, 1), repeat=4):
        symbol_maps: List[Dict[int, int]] = []
        for active_index, coordinate in enumerate(active):
            symbols = sorted({word[coordinate] for word in holes})
            missing = next(symbol for symbol in range(Q) if symbol not in symbols)
            zero_symbol = symbols[flips[active_index]]
            one_symbol = symbols[1 - flips[active_index]]
            symbol_maps.append(
                {zero_symbol: 0, one_symbol: 1, missing: 2}
            )
        for coordinate in inactive:
            fixed = holes[0][coordinate]
            remaining = [symbol for symbol in range(Q) if symbol != fixed]
            symbol_maps.append({fixed: 0, remaining[0]: 1, remaining[1]: 2})

        def transform(word: Word) -> Word:
            return tuple(
                symbol_maps[position][word[coordinate]]
                for position, coordinate in enumerate(ordered_coordinates)
            )

        normalized_hole = {transform(word) for word in holes}
        if normalized_hole == expected_hole:
            return tuple(transform(index.words[center]) for center in centers)
    raise PlateauInvariantError("No J(4,2) normalization was found.")


def canonicalize_pair(
    centers: Sequence[int],
    index: Optional[HammingIndex] = None,
) -> Tuple[Word, ...]:
    """Return the exact lexicographic pair-isometry canonical form."""

    space = index or hamming_index()
    hole_mask = uncovered_mask(centers, space)
    hole_ids = tuple(_iter_bits(hole_mask))
    normalized = _normalize_pair(centers, hole_ids, space)
    best: Optional[Tuple[Word, ...]] = None
    for transform in j42_stabilizer():
        candidate = tuple(
            sorted(_apply_stabilizer(word, transform) for word in normalized)
        )
        if best is None or candidate < best:
            best = candidate
    if best is None:
        raise PlateauInvariantError("Canonicalization produced no candidate.")
    return best


def common_repair_centers(
    hole: Sequence[Word],
    index: Optional[HammingIndex] = None,
) -> Tuple[int, ...]:
    """Return every center whose radius-3 ball contains the complete hole."""

    space = index or hamming_index()
    hole_mask = 0
    for word in hole:
        hole_mask |= 1 << encode(word)
    return tuple(
        center
        for center, ball_mask in enumerate(space.ball_masks)
        if hole_mask & ~ball_mask == 0
    )


@dataclass(frozen=True)
class MaskGroup:
    covered: int
    mask: int
    centers: Tuple[int, ...]


def _coverage_groups(
    hole_mask: int,
    allowed: Sequence[int],
    ball_masks: Sequence[int],
    excluded: Optional[int] = None,
) -> Tuple[MaskGroup, ...]:
    grouped: DefaultDict[int, List[int]] = defaultdict(list)
    for center in allowed:
        if center != excluded:
            grouped[ball_masks[center] & hole_mask].append(center)
    groups = [
        MaskGroup(
            covered=_popcount(mask),
            mask=mask,
            centers=tuple(centers),
        )
        for mask, centers in grouped.items()
    ]
    groups.sort(key=lambda group: (-group.covered, group.mask))
    return tuple(groups)


def _pair_at_most(
    remaining_mask: int,
    allowed: Sequence[int],
    ball_masks: Sequence[int],
    residual_limit: int,
    excluded: Optional[int] = None,
) -> Tuple[Optional[Tuple[int, int]], int, int]:
    target = _popcount(remaining_mask) - residual_limit
    groups = _coverage_groups(remaining_mask, allowed, ball_masks, excluded)
    if len(groups) < 1:
        return None, 0, 0
    available = tuple(center for center in allowed if center != excluded)
    if len(available) < 2:
        return None, 0, len(groups)

    if target <= 0 or groups[0].covered >= target:
        first = groups[0].centers[0]
        second = next(center for center in available if center != first)
        return (first, second), 0, len(groups)

    checks = 0
    largest = groups[0].covered
    for left_index, left in enumerate(groups):
        if left.covered + largest < target:
            break
        for right in groups[left_index + 1 :]:
            if left.covered + right.covered < target:
                break
            checks += 1
            if _popcount(left.mask | right.mask) >= target:
                return (left.centers[0], right.centers[0]), checks, len(groups)
    return None, checks, len(groups)


def _find_three_at_most(
    hole_mask: int,
    allowed: Sequence[int],
    ball_masks: Sequence[int],
    residual_limit: int,
) -> Tuple[Optional[Tuple[int, int, int]], int, int]:
    checks = 0
    signatures = 0
    for first in allowed:
        remaining = hole_mask & ~ball_masks[first]
        pair, pair_checks, pair_signatures = _pair_at_most(
            remaining,
            allowed,
            ball_masks,
            residual_limit,
            excluded=first,
        )
        checks += pair_checks
        signatures += pair_signatures
        if pair is not None:
            return (first, pair[0], pair[1]), checks, signatures
    return None, checks, signatures


def _enumerate_three_at_residual(
    hole_mask: int,
    allowed: Sequence[int],
    ball_masks: Sequence[int],
    residual: int,
) -> Tuple[Tuple[Tuple[int, int, int], ...], int, int]:
    triples: Set[Tuple[int, int, int]] = set()
    checks = 0
    signatures = 0
    for first in allowed:
        remaining = hole_mask & ~ball_masks[first]
        target = _popcount(remaining) - residual
        groups = _coverage_groups(
            remaining,
            allowed,
            ball_masks,
            excluded=first,
        )
        signatures += len(groups)
        if not groups:
            continue
        largest = groups[0].covered
        for left_index, left in enumerate(groups):
            if left.covered > target:
                raise PlateauInvariantError(
                    "A better core completion appeared during enumeration."
                )
            if left.covered == target and len(left.centers) >= 2:
                for second, third in combinations(left.centers, 2):
                    triples.add(tuple(sorted((first, second, third))))
            if left.covered + largest < target:
                break
            for right in groups[left_index + 1 :]:
                if left.covered + right.covered < target:
                    break
                checks += 1
                union_size = _popcount(left.mask | right.mask)
                if union_size > target:
                    raise PlateauInvariantError(
                        "A better core completion appeared during enumeration."
                    )
                if union_size == target:
                    for second in left.centers:
                        for third in right.centers:
                            triples.add(tuple(sorted((first, second, third))))
    return tuple(sorted(triples)), checks, signatures


def _core_stabilizer(core: FrozenSet[Word]) -> Tuple[Transform, ...]:
    stabilizer = tuple(
        transform
        for transform in j42_stabilizer()
        if frozenset(_apply_stabilizer(word, transform) for word in core) == core
    )
    return stabilizer


def _canonical_tail(
    tail: Sequence[Word],
    stabilizer: Sequence[Transform],
) -> Tuple[Word, ...]:
    return min(
        tuple(sorted(_apply_stabilizer(word, transform) for word in tail))
        for transform in stabilizer
    )


@dataclass(frozen=True)
class CoreCompletionResult:
    core_hole_count: int
    minimum_residual: int
    optimal_tails: Tuple[Tuple[Word, ...], ...]
    tail_class_representatives: Tuple[Tuple[Word, ...], ...]
    core_stabilizer_size: int
    raw_candidate_triples: int
    decision_mask_pair_checks: int
    enumeration_mask_pair_checks: int
    decision_signature_rows: int
    enumeration_signature_rows: int


def analyze_core_completion(
    core: Sequence[Word],
    witness_tail: Sequence[Word],
    index: Optional[HammingIndex] = None,
) -> CoreCompletionResult:
    """Solve the exact three-center completion problem for a normalized core."""

    space = index or hamming_index()
    core_ids = frozenset(encode(word) for word in core)
    if len(core_ids) != 8:
        raise PlateauInvariantError("The canonical core must contain eight words.")
    allowed = tuple(center for center in range(WORD_COUNT) if center not in core_ids)
    core_holes = uncovered_mask(core_ids, space)

    witness_ids = tuple(encode(word) for word in witness_tail)
    if len(witness_ids) != 3 or len(set(witness_ids)) != 3:
        raise PlateauInvariantError("The completion witness must have three words.")
    current_witness = witness_ids
    current_residual = uncovered_count(core_ids | set(current_witness), space)

    decision_checks = 0
    decision_signatures = 0
    while current_residual > 0:
        better, checks, signatures = _find_three_at_most(
            core_holes,
            allowed,
            space.ball_masks,
            current_residual - 1,
        )
        decision_checks += checks
        decision_signatures += signatures
        if better is None:
            break
        better_residual = uncovered_count(core_ids | set(better), space)
        if better_residual >= current_residual:
            raise PlateauInvariantError("The completion decision search was inconsistent.")
        current_witness = better
        current_residual = better_residual

    optimal_ids, enumeration_checks, enumeration_signatures = (
        _enumerate_three_at_residual(
            core_holes,
            allowed,
            space.ball_masks,
            current_residual,
        )
    )
    if tuple(sorted(current_witness)) not in optimal_ids:
        raise PlateauInvariantError("The optimum witness was not enumerated.")

    expected_hole = canonical_j42_hole()
    optimal_tails: List[Tuple[Word, ...]] = []
    for tail_ids in optimal_ids:
        final_ids = core_ids | set(tail_ids)
        hole = tuple(
            space.words[point]
            for point in _iter_bits(uncovered_mask(final_ids, space))
        )
        if hole != expected_hole:
            raise PlateauInvariantError("An optimum tail has a different hole.")
        optimal_tails.append(tuple(space.words[center] for center in tail_ids))

    core_words = frozenset(core)
    stabilizer = _core_stabilizer(core_words)
    classes = {
        _canonical_tail(tail, stabilizer)
        for tail in optimal_tails
    }
    return CoreCompletionResult(
        core_hole_count=_popcount(core_holes),
        minimum_residual=current_residual,
        optimal_tails=tuple(sorted(optimal_tails)),
        tail_class_representatives=tuple(sorted(classes)),
        core_stabilizer_size=len(stabilizer),
        raw_candidate_triples=comb(len(allowed), 3),
        decision_mask_pair_checks=decision_checks,
        enumeration_mask_pair_checks=enumeration_checks,
        decision_signature_rows=decision_signatures,
        enumeration_signature_rows=enumeration_signatures,
    )


def _coverage_counts(
    centers: Sequence[int],
    index: HammingIndex,
) -> Tuple[int, ...]:
    counts = [0] * WORD_COUNT
    for center in centers:
        for point in index.ball_points[center]:
            counts[point] += 1
    return tuple(counts)


def _holes_after_removal(
    counts: Sequence[int],
    removed: Sequence[int],
    index: HammingIndex,
) -> int:
    lost = [0] * WORD_COUNT
    for center in removed:
        for point in index.ball_points[center]:
            lost[point] += 1
    result = 0
    for point, total in enumerate(counts):
        if total == lost[point]:
            result |= 1 << point
    return result


def _best_pair_residual(
    hole_mask: int,
    allowed: Sequence[int],
    ball_masks: Sequence[int],
) -> Tuple[int, int, int]:
    groups = _coverage_groups(hole_mask, allowed, ball_masks)
    if not groups:
        raise PlateauInvariantError("No replacement-center signatures were generated.")
    best_covered = 0
    checks = 0
    largest = groups[0].covered
    for left_index, left in enumerate(groups):
        if len(left.centers) >= 2 and left.covered > best_covered:
            best_covered = left.covered
        if left.covered + largest <= best_covered:
            break
        for right in groups[left_index + 1 :]:
            if left.covered + right.covered <= best_covered:
                break
            checks += 1
            covered = _popcount(left.mask | right.mask)
            if covered > best_covered:
                best_covered = covered
    return _popcount(hole_mask) - best_covered, checks, len(groups)


def _pairs_at_residual(
    hole_mask: int,
    allowed: Sequence[int],
    ball_masks: Sequence[int],
    residual: int,
) -> Tuple[Tuple[Tuple[int, int], ...], int, int]:
    target = _popcount(hole_mask) - residual
    groups = _coverage_groups(hole_mask, allowed, ball_masks)
    pairs: Set[Tuple[int, int]] = set()
    checks = 0
    if not groups:
        return (), checks, 0
    largest = groups[0].covered
    for left_index, left in enumerate(groups):
        if left.covered > target:
            raise PlateauInvariantError("A better two-replacement result appeared.")
        if left.covered == target and len(left.centers) >= 2:
            pairs.update(tuple(sorted(pair)) for pair in combinations(left.centers, 2))
        if left.covered + largest < target:
            break
        for right in groups[left_index + 1 :]:
            if left.covered + right.covered < target:
                break
            checks += 1
            union_size = _popcount(left.mask | right.mask)
            if union_size > target:
                raise PlateauInvariantError("A better two-replacement result appeared.")
            if union_size == target:
                for first in left.centers:
                    for second in right.centers:
                        pairs.add(tuple(sorted((first, second))))
    return tuple(sorted(pairs)), checks, len(groups)


@dataclass(frozen=True)
class ReplacementResult:
    strict_one_minimum: int
    strict_one_minima: Tuple[int, ...]
    strict_two_minimum: int
    strict_two_distribution: Tuple[Tuple[int, int], ...]
    plateau_neighbors: Tuple[Tuple[int, ...], ...]
    neighbor_class_counts: Tuple[Tuple[str, int], ...]
    raw_one_candidates: int
    raw_two_candidates: int
    optimization_mask_pair_checks: int
    enumeration_mask_pair_checks: int
    optimization_signature_rows: int
    enumeration_signature_rows: int


@dataclass(frozen=True)
class _ReplacementComputation:
    strict_one_minimum: int
    strict_one_minima: Tuple[int, ...]
    strict_two_minimum: int
    strict_two_distribution: Tuple[Tuple[int, int], ...]
    plateau_neighbors: Tuple[Tuple[int, ...], ...]
    raw_one_candidates: int
    raw_two_candidates: int
    optimization_mask_pair_checks: int
    enumeration_mask_pair_checks: int
    optimization_signature_rows: int
    enumeration_signature_rows: int


def _analyze_replacements(
    centers: Sequence[int],
    index: HammingIndex,
) -> _ReplacementComputation:
    center_set = frozenset(centers)
    allowed = tuple(
        center for center in range(WORD_COUNT) if center not in center_set
    )
    counts = _coverage_counts(centers, index)

    one_minima: List[int] = []
    for removed in centers:
        holes = _holes_after_removal(counts, (removed,), index)
        best = min(
            _popcount(holes & ~index.ball_masks[replacement])
            for replacement in allowed
        )
        one_minima.append(best)

    removal_rows: List[Tuple[Tuple[int, int], int, int]] = []
    optimization_checks = 0
    optimization_signatures = 0
    for removed in combinations(centers, 2):
        holes = _holes_after_removal(counts, removed, index)
        residual, checks, signatures = _best_pair_residual(
            holes,
            allowed,
            index.ball_masks,
        )
        removal_rows.append((removed, holes, residual))
        optimization_checks += checks
        optimization_signatures += signatures

    strict_two_minimum = min(row[2] for row in removal_rows)
    neighbors: Set[Tuple[int, ...]] = set()
    enumeration_checks = 0
    enumeration_signatures = 0
    for removed, holes, residual in removal_rows:
        if residual != strict_two_minimum:
            continue
        pairs, checks, signatures = _pairs_at_residual(
            holes,
            allowed,
            index.ball_masks,
            strict_two_minimum,
        )
        enumeration_checks += checks
        enumeration_signatures += signatures
        retained = center_set - set(removed)
        for first, second in pairs:
            neighbor = tuple(sorted(retained | {first, second}))
            if len(neighbor) != len(centers):
                raise PlateauInvariantError("A replacement produced the wrong code size.")
            if uncovered_count(neighbor, index) != strict_two_minimum:
                raise PlateauInvariantError("A replacement neighbor failed verification.")
            neighbors.add(neighbor)

    distribution = tuple(
        sorted(Counter(row[2] for row in removal_rows).items())
    )
    return _ReplacementComputation(
        strict_one_minimum=min(one_minima),
        strict_one_minima=tuple(sorted(one_minima)),
        strict_two_minimum=strict_two_minimum,
        strict_two_distribution=distribution,
        plateau_neighbors=tuple(sorted(neighbors)),
        raw_one_candidates=len(centers) * len(allowed),
        raw_two_candidates=comb(len(centers), 2) * comb(len(allowed), 2),
        optimization_mask_pair_checks=optimization_checks,
        enumeration_mask_pair_checks=enumeration_checks,
        optimization_signature_rows=optimization_signatures,
        enumeration_signature_rows=enumeration_signatures,
    )


@dataclass(frozen=True)
class PlateauReport:
    canonical_hole: Tuple[Word, ...]
    repair_center_count: int
    canonical_forms: Tuple[Tuple[str, Tuple[Word, ...]], ...]
    canonical_core: Tuple[Word, ...]
    observed_tails: Tuple[Tuple[str, Tuple[Word, ...]], ...]
    core_completion: CoreCompletionResult
    replacements: Tuple[Tuple[str, ReplacementResult], ...]
    adjacency: Tuple[Tuple[str, Tuple[str, ...]], ...]
    plateau_neighbor_count: int


def analyze_plateau(
    labeled_codes: Mapping[str, Sequence[Word]],
    index: Optional[HammingIndex] = None,
) -> PlateauReport:
    """Reproduce the complete retained plateau computation."""

    if len(labeled_codes) != 4:
        raise PlateauInvariantError("Exactly four retained codes are required.")
    space = index or hamming_index()
    normalized_codes: Dict[str, Tuple[int, ...]] = {}
    canonical_forms: Dict[str, Tuple[Word, ...]] = {}

    for label in sorted(labeled_codes):
        ids = code_ids(labeled_codes[label])
        if len(ids) != 11:
            raise PlateauInvariantError("Every retained code must have size 11.")
        if uncovered_count(ids, space) != 6:
            raise PlateauInvariantError("Every retained code must have six holes.")
        normalized_codes[label] = ids
        canonical_forms[label] = canonicalize_pair(ids, space)

    if len(set(canonical_forms.values())) != 4:
        raise PlateauInvariantError("The retained pairs do not form four classes.")

    form_sets = [set(form) for form in canonical_forms.values()]
    core_set = set.intersection(*form_sets)
    if len(core_set) != 8:
        raise PlateauInvariantError("The canonical forms do not share an eight-word core.")
    core = tuple(sorted(core_set))
    observed_tails = {
        label: tuple(sorted(set(form) - core_set))
        for label, form in canonical_forms.items()
    }
    if any(len(tail) != 3 for tail in observed_tails.values()):
        raise PlateauInvariantError("A canonical class does not have a three-word tail.")

    repair_centers = common_repair_centers(canonical_j42_hole(), space)
    core_completion = analyze_core_completion(
        core,
        observed_tails[sorted(observed_tails)[0]],
        space,
    )

    class_by_form = {
        form: label for label, form in canonical_forms.items()
    }
    replacement_results: Dict[str, ReplacementResult] = {}
    adjacency: Dict[str, Tuple[str, ...]] = {}
    plateau_neighbor_count = 0
    for label in sorted(normalized_codes):
        computation = _analyze_replacements(normalized_codes[label], space)
        neighbor_counts: Counter[str] = Counter()
        for neighbor in computation.plateau_neighbors:
            canonical = canonicalize_pair(neighbor, space)
            target = class_by_form.get(canonical)
            if target is None:
                raise PlateauInvariantError(
                    "A plateau neighbor lies outside the four retained classes."
                )
            neighbor_counts[target] += 1
        plateau_neighbor_count += len(computation.plateau_neighbors)
        adjacency[label] = tuple(sorted(neighbor_counts))
        replacement_results[label] = ReplacementResult(
            strict_one_minimum=computation.strict_one_minimum,
            strict_one_minima=computation.strict_one_minima,
            strict_two_minimum=computation.strict_two_minimum,
            strict_two_distribution=computation.strict_two_distribution,
            plateau_neighbors=computation.plateau_neighbors,
            neighbor_class_counts=tuple(sorted(neighbor_counts.items())),
            raw_one_candidates=computation.raw_one_candidates,
            raw_two_candidates=computation.raw_two_candidates,
            optimization_mask_pair_checks=(
                computation.optimization_mask_pair_checks
            ),
            enumeration_mask_pair_checks=(
                computation.enumeration_mask_pair_checks
            ),
            optimization_signature_rows=(
                computation.optimization_signature_rows
            ),
            enumeration_signature_rows=(
                computation.enumeration_signature_rows
            ),
        )

    return PlateauReport(
        canonical_hole=canonical_j42_hole(),
        repair_center_count=len(repair_centers),
        canonical_forms=tuple(sorted(canonical_forms.items())),
        canonical_core=core,
        observed_tails=tuple(sorted(observed_tails.items())),
        core_completion=core_completion,
        replacements=tuple(sorted(replacement_results.items())),
        adjacency=tuple(sorted(adjacency.items())),
        plateau_neighbor_count=plateau_neighbor_count,
    )


def report_to_dict(report: PlateauReport) -> Dict[str, object]:
    core_result = report.core_completion
    replacement_rows: Dict[str, object] = {}
    for label, result in report.replacements:
        replacement_rows[label] = {
            "strict_one_minimum": result.strict_one_minimum,
            "strict_one_minima": list(result.strict_one_minima),
            "strict_two_minimum": result.strict_two_minimum,
            "strict_two_distribution": {
                str(residual): count
                for residual, count in result.strict_two_distribution
            },
            "plateau_neighbor_count": len(result.plateau_neighbors),
            "neighbor_class_counts": dict(result.neighbor_class_counts),
            "raw_one_candidates": result.raw_one_candidates,
            "raw_two_candidates": result.raw_two_candidates,
            "optimization_mask_pair_checks": (
                result.optimization_mask_pair_checks
            ),
            "enumeration_mask_pair_checks": result.enumeration_mask_pair_checks,
            "optimization_signature_rows": result.optimization_signature_rows,
            "enumeration_signature_rows": result.enumeration_signature_rows,
        }
    return {
        "canonical_hole": [word_text(word) for word in report.canonical_hole],
        "repair_center_count": report.repair_center_count,
        "pair_isometry_class_count": len(report.canonical_forms),
        "canonical_forms": {
            label: [word_text(word) for word in form]
            for label, form in report.canonical_forms
        },
        "canonical_core": [
            word_text(word) for word in report.canonical_core
        ],
        "observed_tails": {
            label: [word_text(word) for word in tail]
            for label, tail in report.observed_tails
        },
        "core_completion": {
            "core_hole_count": core_result.core_hole_count,
            "minimum_residual": core_result.minimum_residual,
            "optimal_tail_count": len(core_result.optimal_tails),
            "optimal_tails": [
                [word_text(word) for word in tail]
                for tail in core_result.optimal_tails
            ],
            "tail_class_count": len(core_result.tail_class_representatives),
            "tail_class_representatives": [
                [word_text(word) for word in tail]
                for tail in core_result.tail_class_representatives
            ],
            "core_stabilizer_size": core_result.core_stabilizer_size,
            "raw_candidate_triples": core_result.raw_candidate_triples,
            "decision_mask_pair_checks": (
                core_result.decision_mask_pair_checks
            ),
            "enumeration_mask_pair_checks": (
                core_result.enumeration_mask_pair_checks
            ),
            "decision_signature_rows": core_result.decision_signature_rows,
            "enumeration_signature_rows": (
                core_result.enumeration_signature_rows
            ),
        },
        "replacements": replacement_rows,
        "plateau_neighbor_count": report.plateau_neighbor_count,
        "adjacency": {
            label: list(targets) for label, targets in report.adjacency
        },
    }
