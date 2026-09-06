"""Third-center orbits after fixing a canonical diameter pair.

For branch diameter ``d``, the ordered anchors are

``a = 0000000`` and ``b = 1^d 0^(7-d)``.

This module uses their pointwise stabilizer in the ternary Hamming-space
isometry group.  Such an isometry has exactly the following freedom:

* permute the first ``d`` coordinates among themselves;
* permute the final ``7-d`` coordinates among themselves; and
* independently exchange symbols 1 and 2 in each final coordinate.

No nontrivial symbol permutation is possible in a first-block coordinate,
because both 0 and 1 must be fixed there.  A final-block symbol permutation
must fix 0 and may exchange 1 and 2.

Consequently, a word orbit is determined by the counts of 0, 1, and 2 in
the first block and by the number of nonzero symbols in the final block.
The canonical representative sorts the first block as 0s, then 1s, then
2s, and writes the final block as 0s followed by 1s.  This is the
lexicographically least member of the orbit.

The branch decomposition below is complete for the allowed-center filter
defined in :mod:`ternary_covering_code.branches`.  It does not establish
that a representative extends to a covering code.  Once more centers are
selected, their pairwise distances must still be checked against the exact
branch diameter.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from math import comb, factorial
from typing import Sequence, Tuple

from .branches import (
    BRANCH_DIAMETERS,
    allowed_centers,
    canonical_diameter_pair,
)
from .space import N, Q, Word


@dataclass(frozen=True, order=True)
class StabilizerSignature:
    """Complete invariants for one pointwise anchor-stabilizer orbit."""

    differing_zero_count: int
    differing_one_count: int
    differing_two_count: int
    equal_nonzero_weight: int

    @property
    def differing_symbol_counts(self) -> Tuple[int, int, int]:
        return (
            self.differing_zero_count,
            self.differing_one_count,
            self.differing_two_count,
        )


@dataclass(frozen=True)
class StabilizerOrbit:
    """One allowed-center orbit in a fixed exact-diameter branch."""

    diameter: int
    signature: StabilizerSignature
    representative: Word
    size: int
    contains_anchor: bool


def _validated_diameter(diameter: int) -> int:
    if isinstance(diameter, bool) or not isinstance(diameter, int):
        raise TypeError("Branch diameter must be an integer.")
    if diameter not in BRANCH_DIAMETERS:
        raise ValueError(
            f"Branch diameter must be one of {BRANCH_DIAMETERS}, "
            f"found {diameter}."
        )
    return diameter


def _validated_word(word: Sequence[int]) -> Word:
    result = tuple(word)
    if len(result) != N:
        raise ValueError(f"Expected a word of length {N}, found {len(result)}.")
    if any(symbol not in range(Q) for symbol in result):
        raise ValueError(f"Every symbol must be in 0..{Q - 1}.")
    return result


def _validated_signature(
    diameter: int,
    signature: StabilizerSignature,
) -> StabilizerSignature:
    _validated_diameter(diameter)
    counts = signature.differing_symbol_counts
    if any(count < 0 for count in counts):
        raise ValueError("Differing-block symbol counts must be nonnegative.")
    if sum(counts) != diameter:
        raise ValueError(
            "Differing-block symbol counts must sum to the branch diameter."
        )
    equal_length = N - diameter
    if not 0 <= signature.equal_nonzero_weight <= equal_length:
        raise ValueError(
            "Equal-block nonzero weight must lie between 0 and "
            f"{equal_length}."
        )
    return signature


def stabilizer_order(diameter: int) -> int:
    """Return the order of the pointwise canonical-anchor stabilizer."""

    d = _validated_diameter(diameter)
    equal_length = N - d
    return (
        factorial(d)
        * factorial(equal_length)
        * 2**equal_length
    )


def stabilizer_signature(
    diameter: int,
    center: Sequence[int],
) -> StabilizerSignature:
    """Return the complete orbit invariant of one ambient center."""

    d = _validated_diameter(diameter)
    word = _validated_word(center)
    differing = word[:d]
    equal = word[d:]
    return StabilizerSignature(
        differing_zero_count=differing.count(0),
        differing_one_count=differing.count(1),
        differing_two_count=differing.count(2),
        equal_nonzero_weight=sum(symbol != 0 for symbol in equal),
    )


def canonical_orbit_representative(
    diameter: int,
    center: Sequence[int],
) -> Word:
    """Return the lexicographically least word in the stabilizer orbit."""

    signature = stabilizer_signature(diameter, center)
    equal_zero_count = (
        N - diameter - signature.equal_nonzero_weight
    )
    return (
        (0,) * signature.differing_zero_count
        + (1,) * signature.differing_one_count
        + (2,) * signature.differing_two_count
        + (0,) * equal_zero_count
        + (1,) * signature.equal_nonzero_weight
    )


def orbit_size_from_signature(
    diameter: int,
    signature: StabilizerSignature,
) -> int:
    """Return the orbit size implied by a validated complete signature."""

    d = _validated_diameter(diameter)
    signature = _validated_signature(d, signature)
    zero_count, one_count, two_count = (
        signature.differing_symbol_counts
    )
    differing_arrangements = (
        factorial(d)
        // (
            factorial(zero_count)
            * factorial(one_count)
            * factorial(two_count)
        )
    )
    equal_arrangements = (
        comb(N - d, signature.equal_nonzero_weight)
        * 2**signature.equal_nonzero_weight
    )
    return differing_arrangements * equal_arrangements


@lru_cache(maxsize=None)
def _members_from_signature(
    diameter: int,
    signature: StabilizerSignature,
) -> Tuple[Word, ...]:
    d = _validated_diameter(diameter)
    signature = _validated_signature(d, signature)
    expected_counts = signature.differing_symbol_counts
    differing_words = tuple(
        word
        for word in product(range(Q), repeat=d)
        if tuple(word.count(symbol) for symbol in range(Q))
        == expected_counts
    )
    equal_words = tuple(
        word
        for word in product(range(Q), repeat=N - d)
        if sum(symbol != 0 for symbol in word)
        == signature.equal_nonzero_weight
    )
    return tuple(
        differing + equal
        for differing in differing_words
        for equal in equal_words
    )


def stabilizer_orbit_members(
    diameter: int,
    center: Sequence[int],
) -> Tuple[Word, ...]:
    """Enumerate every image of a center under the pointwise stabilizer."""

    signature = stabilizer_signature(diameter, center)
    return _members_from_signature(diameter, signature)


def orbit_members(orbit: StabilizerOrbit) -> Tuple[Word, ...]:
    """Enumerate the members represented by one orbit record."""

    members = _members_from_signature(orbit.diameter, orbit.signature)
    if len(members) != orbit.size:
        raise AssertionError("Stored orbit size does not match enumeration.")
    return members


@lru_cache(maxsize=None)
def allowed_center_orbits(
    diameter: int,
) -> Tuple[StabilizerOrbit, ...]:
    """Partition every anchor-compatible center into stabilizer orbits."""

    d = _validated_diameter(diameter)
    centers = allowed_centers(d)
    signatures = {
        stabilizer_signature(d, center)
        for center in centers
    }
    anchors = set(canonical_diameter_pair(d))
    records = []
    for signature in signatures:
        representative = canonical_orbit_representative(
            d,
            _members_from_signature(d, signature)[0],
        )
        members = _members_from_signature(d, signature)
        if representative not in centers:
            raise AssertionError(
                "An allowed-center orbit has a representative outside "
                "the branch filter."
            )
        if any(member not in centers for member in members):
            raise AssertionError(
                "The allowed-center filter is not invariant under the "
                "anchor stabilizer."
            )
        records.append(
            StabilizerOrbit(
                diameter=d,
                signature=signature,
                representative=representative,
                size=orbit_size_from_signature(d, signature),
                contains_anchor=any(anchor in members for anchor in anchors),
            )
        )
    return tuple(sorted(records, key=lambda orbit: orbit.representative))


@lru_cache(maxsize=None)
def third_center_orbits(
    diameter: int,
) -> Tuple[StabilizerOrbit, ...]:
    """Return allowed orbits for a third center distinct from both anchors."""

    return tuple(
        orbit
        for orbit in allowed_center_orbits(diameter)
        if not orbit.contains_anchor
    )
