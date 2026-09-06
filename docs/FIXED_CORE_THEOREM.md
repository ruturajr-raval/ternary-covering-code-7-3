# Eight-Word Core Completion Theorem

Status date: 2026-09-06

## Core

Work in the ternary Hamming space `H(7,3) = {0,1,2}^7` with covering
radius 3. Define

```text
C0 = {
  0000011, 0000102, 0000220, 0002121,
  1111022, 1111110, 1111201, 2222000
}.
```

Direct enumeration shows that `C0` leaves 253 ambient words uncovered.

## Theorem

For every set `T` of at most three additional centers,

```text
|H(7,3) \ union_{c in C0 union T} B_3(c)| >= 6.
```

Equality is attained by exactly eight unordered three-center sets.

Consequently, no ternary radius-3 covering code of size at most 11 contains
`C0` or an isometric copy of `C0`.

## Why Three-Center Enumeration Is Complete

There are 2,187 ambient centers. Excluding the eight fixed core centers leaves
2,179 allowed added centers. The direct verifier checks every strictly
ordered index triple

```text
0 <= i < j < k < 2179.
```

The number checked is

```text
binom(2179,3) = 1,721,956,929.
```

If fewer than three centers formed a cover, adding arbitrary distinct centers
could only improve coverage and would produce a three-center completion.
Therefore the exact three-center minimum also proves the statement for at
most three centers.

## Optimal Triples

The eight minimizing triples are:

```text
1112212 2220111 2221222
1112212 2220121 2221212
1112212 2220122 2221211
1112212 2220212 2221121
1112212 2220221 2221112
1121212 2212212 2220121
1211212 2122212 2220121
1222212 2111212 2220121
```

Each leaves the same normalized six-word hole:

```text
0011000
0101000
0110000
1001000
1010000
1100000
```

The core stabilizer has order 18 and partitions the eight triples into four
orbits.

## Independent Implementations

### Python exact mask analysis

`src/ternary_covering_code/plateau.py` constructs every radius-3 ball and
solves the exact completion problem on the 253 core holes. Centers with
identical coverage on the current finite hole set are grouped only after
their full coverage masks are computed.

The implementation reports:

```text
raw triples:                    1,721,956,929
decision mask-pair checks:            953,817
enumeration mask-pair checks:       1,037,029
minimum residual:                           6
optimal triples:                             8
```

### Rust direct scan

`search/src/bin/core_direct.rs` reconstructs the Hamming space independently.
It uses four 64-bit words to represent coverage of the 253 holes, but it does
not group centers or prune triples. It directly scans every unordered triple
and independently recovers the same minimum and the same eight triples.

Single-worker and parallel executions are both retained as CI gates.

## SAT Encoding

`src/ternary_covering_code/core_completion_cnf.py` provides a separate CNF
encoding of the residual-at-most-5 and residual-at-most-6 completion
questions. The residual-at-most-6 formula has a checked SAT witness.

No completed residual-at-most-5 UNSAT proof is claimed. The theorem rests on
the two finite enumeration implementations, not on a SAT status.

## Scope

This theorem excludes one explicit core and all of its isometric copies from
every size-at-most-11 cover. It does not show that every hypothetical
11-word cover must contain this core, and it does not change the global
interval `11 <= K_3(7,3) <= 12`.

The stronger theorem in `docs/SEVEN_WORD_SUBCORE_THEOREM.md` deletes each
word of this core in turn and proves the same residual-six minimum after four
added centers. The present theorem remains useful because it additionally
classifies all eight minimizing three-center completions of the full
eight-word core.
