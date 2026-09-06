# Experiment Log

## 2026-09-05 - Baseline Reconstruction

Command:

```text
search/target/release/ternary-covering-search \
  --size 12 --restarts 20 --steps 10000 --seed 1
```

Result:

```text
result_size=12
uncovered=0
```

The recovered code differs from the retained historical-baseline
reconstruction and independently confirms that the local-search
implementation can reach the known upper bound.

## 2026-09-05 - Size-11 Parallel Campaign

Each run used:

```text
--size 11 --restarts 16 --steps 10000
```

Results:

| Seed | Best uncovered | Retained file |
|---:|---:|---|
| 101 | 6 | `data/search/seed_101_best_11.txt` |
| 202 | 6 | `data/search/seed_202_best_11.txt` |
| 303 | 6 | `data/search/seed_303_best_11.txt` |
| 404 | 6 | `data/search/seed_404_best_11.txt` |

No 11-word cover was found. This does not exclude one.

All four candidates have:

- 11 distinct centers;
- nearest-distance distribution ending with six words at distance 4;
- column symbol-count partition `(4,4,3)` in every coordinate;
- uncovered-set pair distances consisting of 12 pairs at distance 2 and
  three pairs at distance 4; and
- exactly 30 centers whose radius-3 ball covers all six uncovered words.

Seeds 101, 303, and 404 share the codeword-distance distribution

```text
d3: 12, d4: 5, d5: 6, d6: 30, d7: 2.
```

Seed 202 has

```text
d3: 12, d4: 4, d5: 7, d6: 31, d7: 1.
```

These invariants do not establish isometry or non-isometry.

## 2026-09-05 - Exchange Search

The independent Rust binary `exchange` combines exhaustive two-center
repairs with three-center large-neighborhood moves.

Campaign:

```text
4 restarts
1,320 large-neighborhood rounds
8 exhaustive two-center scans
```

The campaign was repeated deterministically and again reached six uncovered
words. It did not find an 11-word cover.

## 2026-09-05 - Exact Diameter Reduction

Any radius-3 cover of diameter at most 4 has at least 17 centers. The direct
counting proof is recorded in `docs/DIAMETER_REDUCTION.md`.

The exact diameter-4 at-most-11 CNF supplied a redundant computational
cross-check:

```text
primary variables: 2,187
total variables:   6,237
clauses:          51,126
solver status:    UNSAT
proof replay:     VERIFIED
```

The remaining normalized diameter branches have these third-center orbit
counts:

| Diameter | Allowed centers | Eligible third-center orbits |
|---:|---:|---:|
| 5 | 1,163 | 32 |
| 6 | 1,933 | 41 |
| 7 | 2,187 | 34 |

The lower-bound campaign first targets at-most-10 formulas in these 107
branches. Closing all of them would independently certify
`K_3(7,3) >= 11`.

## 2026-09-05 - Six-Hole Plateau Classification

Exact pair-isometry canonicalization proved that the four retained code-hole
pairs are mutually non-isometric. After normalization, each uncovered set is

```text
0011000
0101000
0110000
1001000
1010000
1100000
```

and all four canonical codes share the eight-word core

```text
0000011
0000102
0000220
0002121
1111022
1111110
1111201
2222000
```

The exact replacement analysis obtained:

| Class | Strict one minimum | Strict two minimum | Plateau neighbors |
|---|---:|---:|---:|
| A | 15 | 6 | 14 |
| B | 15 | 6 | 6 |
| C | 18 | 6 | 5 |
| D | 15 | 6 | 5 |

The strict two-center computation represents 520,608,000 raw candidate
codes. The retained exact-mask implementation preserves the multiplicity of
every represented center pair, and exhaustive small-universe controls compare
its pair reductions with direct enumeration. No second full implementation of
this supporting replacement computation is claimed.

## 2026-09-05 - Fixed-Core Completion Theorem

The Python exact completion analysis found:

```text
core holes:                       253
allowed added centers:          2,179
raw unordered triples:  1,721,956,929
minimum residual holes:             6
minimizing triples:                  8
core stabilizer order:              18
stabilizer classes:                  4
```

The independent Rust binary `core_direct` reconstructs the Hamming space and
directly scans every unordered triple without mask grouping. One-worker and
14-worker executions returned the same minimum and the same ordered list of
eight minimizing triples.

The eight triples are recorded in `docs/FIXED_CORE_THEOREM.md`.

## 2026-09-05 - Seven-Word Subcore Exclusion

Deleting one word from the eight-word core gives eight seven-word subcores.
The order-18 core stabilizer partitions these deletions into four orbits:

| Representative | Orbit size | Initial holes |
|---|---:|---:|
| `0000011` | 3 | 370 |
| `0002121` | 1 | 358 |
| `1111022` | 3 | 396 |
| `2222000` | 1 | 518 |

For a residual-at-most-5 four-center completion, pair averaging proves that
one of the six center pairs must cover at least
`ceil((initial_holes - 5) / 2)` holes. The exact thresholds and eligible
first-pair counts are:

| Representative | Threshold | Eligible first pairs |
|---|---:|---:|
| `0000011` | 183 | 86,319 |
| `0002121` | 177 | 81,290 |
| `1111022` | 196 | 82,464 |
| `2222000` | 257 | 97,292 |

Each representative has 2,180 candidate centers and 2,375,110 unordered
candidate pairs. The complete computation builds:

```text
total pair entries:            9,500,440
eligible first pairs queried:    347,365
residual-at-most-5 completion:       none
exact minimum residual:                  6
```

For every representative, adding the deleted word together with
`1112212`, `2220121`, and `2221212` leaves the same canonical six-word hole.

The Rust verifier permits overlapping pair witnesses and pads to four
distinct centers. The independent C++20 verifier requires disjoint pairs and
reconstructs the stabilizer separately. Both return the same orbit data,
counts, drift checks, minima, and witnesses.

Release hardening added:

- a safe worker range of 1 through 64 in both command-line interfaces;
- explicit rejection of signed and oversized worker counts;
- 63-, 64-, and 65-bit pair-index boundary controls;
- 517- and 518-bit full-mask boundary controls;
- default-compiler, Clang, and sanitizer-backed C++20 self-tests; and
- automatic comparison of fresh Rust and C++20 outputs with the checked
  machine-readable evidence record.

This proves that no size-at-most-11 cover contains any of the eight
seven-word subcores or an isometric copy. It does not exclude candidate
codes containing none of these subcores.

## 2026-09-05 - Independent CNF Boundary Check

The separate fixed-core CNF has:

| Residual limit | Variables | Clauses | Status |
|---:|---:|---:|---|
| 5 | 10,234 | 18,265 | unresolved |
| 6 | 10,486 | 18,767 | SAT |

The residual-6 model extracts three centers and exactly six actual uncovered
core holes. Residual-5 solver runs did not complete, and one partial proof
stream was stopped before disk exhaustion. No UNSAT result is claimed.

The fixed-core theorem relies on the complete Python and Rust enumerations,
not on the unresolved SAT run.

## 2026-09-05 - Adversarial Review

Independent review:

- reproduced the 253-hole geometry and all principal counts;
- checked that the Rust partition enumerates every triple exactly once;
- compared one-, two-, three-, seven-, thirteen-, fourteen-, seventeen-, and
  2,177-worker executions;
- inspected generated machine code for the direct nested loops and vector
  population counts;
- tested pair-mask pruning on all 65,536 four-mask synthetic instances; and
- approved the fixed-core theorem with the explicit global nonclaim.

The stronger seven-word result received a separate adversarial review that:

- checked the pair-averaging lemma and its ceiling arithmetic;
- verified that the four deletion orbits cover all eight core words;
- compared the Rust overlap-and-padding semantics with the C++ disjoint-pair
  semantics;
- ran 6,480 end-to-end synthetic Rust controls against direct four-set
  enumeration;
- ran the independent C++20 pair-index and four-center controls;
- reproduced the complete four-representative outputs in both
  implementations; and
- approved the seven-word theorem with the unchanged global interval.

## Invalid Inference Guard

- Six uncovered words is not a lower bound.
- Repeated convergence is not proof of optimality.
- A timeout or stagnant local search is not an exclusion.
- Only a verified 11-word construction or complete proof certificate can
  change the exact-value status.
