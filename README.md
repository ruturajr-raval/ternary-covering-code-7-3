# Ternary Covering Code `K_3(7,3)`

This repository develops reproducible search and certification methods for
the unresolved ternary covering-code value

```text
K_3(7,3).
```

The current audited interval is

```text
11 <= K_3(7,3) <= 12.
```

The ambient space contains `3^7 = 2,187` words. Every radius-3 Hamming ball
contains 379 words.

## Current Status

The workbench independently reconstructs and verifies a 12-word radius-3
cover. This reproduces the known upper bound:

```text
0000000
0001012
0002021
0022010
0212211
1102110
1121101
1210222
2000011
2120122
2211220
2212202
```

Two independent verification paths cover all 2,187 ambient words:

1. Direct minimum-distance enumeration.
2. Explicit generation and union of every radius-3 ball.

The exact value remains open. No 11-word construction, no exclusion of all
11-word codes, and no project-original global bound improvement is claimed.

## Objective

The project has two decisive routes:

1. Find an 11-word cover and independently certify the known lower bound 11.
2. Prove that no 11-word cover exists and verify a 12-word construction.

Either route requires a self-contained certificate. A solver timeout or an
unsuccessful search is not an impossibility result.

## Reproduction

Verify the retained 12-word code:

```bash
make verify
```

Run the Python test suite:

```bash
make test
```

Run the Rust search tests:

```bash
make test-search
```

Generate the anchored at-most-11 SAT instance:

```bash
make cnf-11
```

The anchor fixes `0000000` as a selected center. This is complete because
translation acts transitively on ternary Hamming space.

## Evidence Standard

Any exact-value claim must include:

- an explicit construction or a complete exclusion;
- deterministic instance generation;
- an independently checked proof or exhaustive certificate;
- separate construction verifiers;
- hashes, tool versions, and replay commands;
- a refreshed prior-art audit; and
- an explicit account of what remains unresolved.

## Authorship

Ruturaj R Raval

ORCID: `0000-0003-4930-8981`

## License

Project code is released under the MIT License. Historical papers and tables
are cited as prior art and are not redistributed.
