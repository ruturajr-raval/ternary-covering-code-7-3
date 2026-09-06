# Diameter Reduction

## Theorem

Every ternary length-7 code with covering radius at most 3 and diameter at
most 4 contains at least 17 centers.

Consequently, every radius-3 cover with at most 16 centers has diameter 5, 6,
or 7.

## Proof

Translate one code center to `0000000` by an isometry of ternary Hamming
space. The diameter assumption then implies that every center has Hamming
weight at most 4.

Consider the 128 full-support words

```text
{1,2}^7.
```

A center of weight at most 3 is at distance at least 4 from every such word,
so it covers none of them. A weight-4 center covers a full-support word
within radius 3 only when all four nonzero symbols agree on the center's
support. The other three symbols are free, so one weight-4 center covers
exactly `2^3 = 8` full-support words.

The translated zero center covers none of the 128 words. Therefore

```text
128 <= 8 (|C| - 1),
```

which gives `|C| >= 17`.

## Computational Cross-Checks

The test suite exhaustively checks the per-center count over all 2,187
ambient centers and all 128 full-support words.

The exact diameter-4 at-most-11 CNF was also proved unsatisfiable by Kissat.
Its DRAT trace was independently accepted by `drat-trim`. This solver result
is a redundant cross-check, not a dependency of the counting proof.

## Scope

This reduction does not decide whether an 11-word cover exists. It removes
the diameter-4 branch and leaves exact diameter 5, 6, and 7.
