"""Deterministic diameter-pair branches for the K_3(7,3) search.

Mathematical scope
------------------
The branch coverage statement uses only these assumptions:

* The ambient space is ``{0, 1, 2}^7`` with Hamming distance.
* A code is a nonempty subset of the ambient space.
* Its radius-3 balls cover the entire ambient space.
* A branch anchor pair is required to realize the code diameter.

For any center ``c``, change every coordinate to obtain a word ``x`` at
distance 7 from ``c``.  Some code center ``c'`` covers ``x``, so

``distance(c, c') >= distance(c, x) - distance(x, c') >= 7 - 3 = 4``.

Every covering code therefore has diameter in ``{4, 5, 6, 7}``.  A
diameter-realizing pair at distance ``d`` can be sent by a Hamming-space
isometry to ``0000000`` and ``1^d 0^(7-d)``.

The allowed-center list for branch ``d`` is a necessary anchor filter:
every center must be within distance ``d`` of both anchors.  It is not
sufficient by itself.  A selected code must also contain both anchors and
must have every pair of selected centers at distance at most ``d``.
No function in this module claims that any branch contains a radius-3 cover.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from typing import Iterable, Sequence, Tuple

from .space import N, Q, RADIUS, Word, all_words, hamming_distance


BRANCH_DIAMETERS = tuple(range(N - RADIUS, N + 1))
BRANCH_ASSUMPTIONS = (
    "Ambient words are the elements of {0,1,2}^7 with Hamming distance.",
    "A code is a nonempty subset of the ambient space.",
    "The radius-3 balls around the code centers cover every ambient word.",
    "The two anchors chosen for a branch realize the code diameter.",
    "Allowed centers satisfy only the necessary anchor-distance filter.",
    "A branch code must additionally contain both anchors and be pairwise "
    "within the branch diameter.",
)


def _validated_word(word: Sequence[int]) -> Word:
    result = tuple(word)
    if len(result) != N:
        raise ValueError(f"Expected a word of length {N}, found {len(result)}.")
    if any(symbol not in range(Q) for symbol in result):
        raise ValueError(f"Every symbol must be in 0..{Q - 1}.")
    return result


def covering_diameter_lower_bound() -> int:
    """Return the lower bound forced by length 7 and covering radius 3.

    The proof is the antipodal-word argument stated in the module docstring.
    It does not use a bound on the number of code centers.
    """

    return N - RADIUS


def branch_diameters() -> Tuple[int, ...]:
    """Return all possible diameters under the documented cover assumptions."""

    return BRANCH_DIAMETERS


def antipode(word: Sequence[int]) -> Word:
    """Return a deterministic word at Hamming distance 7 from ``word``."""

    center = _validated_word(word)
    return tuple((symbol + 1) % Q for symbol in center)


def canonical_diameter_pair(diameter: int) -> Tuple[Word, Word]:
    """Return ``0000000`` and ``1^d 0^(7-d)``."""

    if isinstance(diameter, bool) or not isinstance(diameter, int):
        raise TypeError("Diameter must be an integer.")
    if not 0 <= diameter <= N:
        raise ValueError(f"Diameter must be in 0..{N}.")
    zero = (0,) * N
    second = (1,) * diameter + (0,) * (N - diameter)
    return zero, second


@dataclass(frozen=True)
class HammingIsometry:
    """A coordinate permutation followed by independent symbol permutations."""

    source_coordinates: Tuple[int, ...]
    symbol_images: Tuple[Tuple[int, ...], ...]

    def __post_init__(self) -> None:
        if tuple(sorted(self.source_coordinates)) != tuple(range(N)):
            raise ValueError("Source coordinates must be a permutation of 0..6.")
        if len(self.symbol_images) != N:
            raise ValueError(f"Expected {N} coordinate symbol maps.")
        expected_symbols = tuple(range(Q))
        for images in self.symbol_images:
            if tuple(sorted(images)) != expected_symbols:
                raise ValueError("Each coordinate symbol map must be a permutation.")

    def apply(self, word: Sequence[int]) -> Word:
        """Apply the isometry to one ambient word."""

        source_word = _validated_word(word)
        return tuple(
            self.symbol_images[source][source_word[source]]
            for source in self.source_coordinates
        )

    def invert(self, word: Sequence[int]) -> Word:
        """Apply the inverse isometry to one ambient word."""

        image_word = _validated_word(word)
        source_word = [0] * N
        for output_coordinate, source_coordinate in enumerate(
            self.source_coordinates
        ):
            images = self.symbol_images[source_coordinate]
            inverse = [0] * Q
            for source_symbol, image_symbol in enumerate(images):
                inverse[image_symbol] = source_symbol
            source_word[source_coordinate] = inverse[image_word[output_coordinate]]
        return tuple(source_word)


@dataclass(frozen=True)
class NormalizedPair:
    """The deterministic normalization certificate for one distinct pair."""

    diameter: int
    source_pair: Tuple[Word, Word]
    canonical_pair: Tuple[Word, Word]
    isometry: HammingIsometry


def normalizing_isometry(
    left: Sequence[int],
    right: Sequence[int],
) -> HammingIsometry:
    """Construct a deterministic isometry sending a pair to canonical form."""

    left_word = _validated_word(left)
    right_word = _validated_word(right)
    if left_word == right_word:
        raise ValueError("A diameter pair must contain two distinct words.")

    differing = tuple(
        index
        for index, (left_symbol, right_symbol) in enumerate(
            zip(left_word, right_word)
        )
        if left_symbol != right_symbol
    )
    equal = tuple(index for index in range(N) if index not in differing)
    source_coordinates = differing + equal

    symbol_images = []
    for left_symbol, right_symbol in zip(left_word, right_word):
        images = [-1] * Q
        images[left_symbol] = 0
        if left_symbol != right_symbol:
            images[right_symbol] = 1
            remaining_symbol = next(
                symbol
                for symbol in range(Q)
                if symbol not in (left_symbol, right_symbol)
            )
            images[remaining_symbol] = 2
        else:
            remaining_symbols = [
                symbol for symbol in range(Q) if symbol != left_symbol
            ]
            for image_symbol, source_symbol in enumerate(
                remaining_symbols,
                start=1,
            ):
                images[source_symbol] = image_symbol
        symbol_images.append(tuple(images))

    return HammingIsometry(
        source_coordinates=source_coordinates,
        symbol_images=tuple(symbol_images),
    )


def normalize_diameter_pair(
    left: Sequence[int],
    right: Sequence[int],
) -> NormalizedPair:
    """Return a certificate mapping a distinct pair to canonical anchors."""

    left_word = _validated_word(left)
    right_word = _validated_word(right)
    isometry = normalizing_isometry(left_word, right_word)
    diameter = hamming_distance(left_word, right_word)
    canonical_pair = canonical_diameter_pair(diameter)
    normalized_pair = (
        isometry.apply(left_word),
        isometry.apply(right_word),
    )
    if normalized_pair != canonical_pair:
        raise AssertionError("Pair normalization failed.")
    return NormalizedPair(
        diameter=diameter,
        source_pair=(left_word, right_word),
        canonical_pair=canonical_pair,
        isometry=isometry,
    )


@lru_cache(maxsize=None)
def allowed_centers(diameter: int) -> Tuple[Word, ...]:
    """Enumerate centers compatible with both canonical diameter anchors."""

    if isinstance(diameter, bool) or not isinstance(diameter, int):
        raise TypeError("Branch diameter must be an integer.")
    if diameter not in BRANCH_DIAMETERS:
        raise ValueError(
            f"Branch diameter must be one of {BRANCH_DIAMETERS}, "
            f"found {diameter}."
        )
    left, right = canonical_diameter_pair(diameter)
    return tuple(
        center
        for center in all_words()
        if hamming_distance(center, left) <= diameter
        and hamming_distance(center, right) <= diameter
    )


@dataclass(frozen=True)
class DiameterBranch:
    """One exact-diameter branch after canonical pair normalization."""

    diameter: int
    anchors: Tuple[Word, Word]
    allowed_centers: Tuple[Word, ...]

    def center_is_allowed(self, center: Sequence[int]) -> bool:
        return _validated_word(center) in self.allowed_centers

    def code_is_admissible(
        self,
        code: Iterable[Sequence[int]],
        require_anchors: bool = True,
    ) -> bool:
        """Check all exact branch constraints, except the covering property."""

        centers = tuple(sorted({_validated_word(center) for center in code}))
        if not centers:
            return False
        if require_anchors and not set(self.anchors).issubset(centers):
            return False
        if any(center not in self.allowed_centers for center in centers):
            return False
        return all(
            hamming_distance(left, right) <= self.diameter
            for left, right in combinations(centers, 2)
        )


@lru_cache(maxsize=None)
def diameter_branch(diameter: int) -> DiameterBranch:
    """Build one deterministic branch."""

    return DiameterBranch(
        diameter=diameter,
        anchors=canonical_diameter_pair(diameter),
        allowed_centers=allowed_centers(diameter),
    )


def diameter_branches() -> Tuple[DiameterBranch, ...]:
    """Build the complete ordered branch family for radius-3 covers."""

    return tuple(diameter_branch(diameter) for diameter in BRANCH_DIAMETERS)


def diameter_realizing_pair(
    code: Iterable[Sequence[int]],
) -> Tuple[Word, Word]:
    """Return the lexicographically first pair attaining the code diameter."""

    centers = tuple(sorted({_validated_word(center) for center in code}))
    if len(centers) < 2:
        raise ValueError("At least two distinct centers are required.")

    best_pair = None
    best_distance = -1
    for left, right in combinations(centers, 2):
        distance = hamming_distance(left, right)
        if distance > best_distance:
            best_pair = (left, right)
            best_distance = distance
    if best_pair is None:
        raise AssertionError("No diameter pair was found.")
    return best_pair


@dataclass(frozen=True)
class NormalizedCode:
    """A code and its deterministic assignment to one diameter branch."""

    diameter: int
    source_pair: Tuple[Word, Word]
    centers: Tuple[Word, ...]
    isometry: HammingIsometry


def normalize_code_on_diameter_pair(
    code: Iterable[Sequence[int]],
) -> NormalizedCode:
    """Normalize a code using its lexicographically first diameter pair.

    Codes of diameter below 4 are rejected because the returned branch family
    is complete only under the documented radius-3 covering assumption.
    The function does not independently test the covering property.
    """

    centers = tuple(sorted({_validated_word(center) for center in code}))
    source_pair = diameter_realizing_pair(centers)
    pair = normalize_diameter_pair(*source_pair)
    if pair.diameter not in BRANCH_DIAMETERS:
        raise ValueError(
            "Code diameter is outside the branch family; a radius-3 cover "
            f"would have diameter in {BRANCH_DIAMETERS}."
        )

    normalized_centers = tuple(
        sorted(pair.isometry.apply(center) for center in centers)
    )
    branch = diameter_branch(pair.diameter)
    if not branch.code_is_admissible(normalized_centers):
        raise AssertionError("Normalized code violates its diameter branch.")
    return NormalizedCode(
        diameter=pair.diameter,
        source_pair=source_pair,
        centers=normalized_centers,
        isometry=pair.isometry,
    )
