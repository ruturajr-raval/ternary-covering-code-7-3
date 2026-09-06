# Seven-Word Subcore Exclusion Theorem

Status date: 2026-09-06

## Definitions

Work in `H(7,3) = {0,1,2}^7` with covering radius 3. For a code `D`, write
`U(D)` for the set of words at distance greater than 3 from every word of
`D`.

Define

```text
C0 = {
  0000011, 0000102, 0000220, 0002121,
  1111022, 1111110, 1111201, 2222000
}.
```

For each `c` in `C0`, define the seven-word subcore

```text
S_c = C0 \ {c}.
```

## Theorem

For every `c` in `C0` and every set `T` of at most four ternary length-7
words,

```text
|U(S_c union T)| >= 6.
```

Equality is attained. Consequently, no radius-3 covering code of size at
most 11 contains `S_c` or an isometric copy of `S_c`.

## Symmetry Reduction

The stabilizer of `C0` has order 18. Its action on the eight possible
deleted words has four orbits:

| Representative | Orbit members | Orbit size |
|---|---|---:|
| `0000011` | `0000011`, `0000102`, `0000220` | 3 |
| `0002121` | `0002121` | 1 |
| `1111022` | `1111022`, `1111110`, `1111201` | 3 |
| `2222000` | `2222000` | 1 |

It is therefore sufficient to solve the four representative completion
problems. Isometries preserve Hamming distance, uncovered-set cardinality,
and code cardinality.

## Four-Center Reduction

Fix one seven-word subcore and suppose four added centers cover all but at
most five of its `h` holes.

There are six unordered pairs among the four centers. A hole covered by at
least one center belongs to at least three pair unions: if exactly one center
covers it, the hole belongs to the three pairs containing that center, and
additional covering centers can only increase this count.

The sum of the six pair-union coverage counts is therefore at least

```text
3(h - 5).
```

At least one pair covers at least

```text
ceil((h - 5) / 2)
```

holes. The verifier enumerates every unordered first pair meeting this
threshold and checks every possible complementary pair for coverage of all
but five holes.

This reduction is complete. Any forbidden four-center completion supplies
one of the queried first pairs and its complementary pair. A completion
using fewer than four centers can be augmented with distinct centers without
losing coverage, so exclusion at four centers also excludes all smaller
additions.

## Exact Results

Each representative has 2,180 allowed added centers and
`binom(2180,2) = 2,375,110` unordered candidate pairs.

| Representative | Initial holes | Threshold | Eligible first pairs | Residual `0..5` completion | Exact minimum |
|---|---:|---:|---:|---|---:|
| `0000011` | 370 | 183 | 86,319 | none | 6 |
| `0002121` | 358 | 177 | 81,290 | none | 6 |
| `1111022` | 396 | 196 | 82,464 | none | 6 |
| `2222000` | 518 | 257 | 97,292 | none | 6 |

Across all representatives:

```text
pair entries built:            9,500,440
eligible first pairs queried:    347,365
minimum residual in each case:          6
deletions covered by orbits:             8
```

For each representative `c`, the four additions

```text
c
1112212
2220121
2221212
```

leave exactly

```text
0011000
0101000
0110000
1001000
1010000
1100000
```

uncovered. These witnesses prove attainability of residual six.

## Independent Implementations

### Rust verifier

`search/src/bin/seven_core_direct.rs` independently reconstructs `H(7,3)`,
the radius-3 balls, the core stabilizer, deletion orbits, and all candidate
coverage masks. It builds a pair-union index and queries every eligible first
pair.

The Rust search permits the two pair witnesses to overlap. Any found union of
at most four centers is padded to four distinct centers before its residual
is accepted. This cannot create a false completion witness because adding
centers cannot increase the residual.

### C++20 verifier

`src/seven_core_independent.cpp` separately reconstructs the same finite
objects. It uses a different pair-tree representation and requires the
queried pairs to be disjoint. It also reconstructs the order-18 stabilizer
from Hamming-space isometries rather than importing the Rust orbit data.

Both verifiers independently reproduce the same four orbit representatives,
initial hole counts, thresholds, eligible-pair counts, drift checks, and
minimum residuals. The explicit six-hole equality witness is supplied to
both implementations and verified directly rather than discovered
independently.

## Scope

The theorem excludes eight explicit seven-word subcores and all of their
isometric copies from every size-at-most-11 cover.

It does not prove that every hypothetical 11-word cover contains one of these
subcores. It does not construct an 11-word cover, exclude all 11-word covers,
or change the global interval `11 <= K_3(7,3) <= 12`.
