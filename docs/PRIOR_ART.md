# Prior Art And Novelty Audit

Status date: 2026-09-06

## Public Frontier

Gabor Keri's ternary covering-code table records

```text
11 <= K_3(7,3) <= 12.
```

Sources:

- `https://old.sztaki.hu/~keri/codes/3_tables.pdf`
- `https://old.sztaki.hu/~keri/codes/index.htm`

The table associates the upper bound 12 with:

- H. Hamalainen and S. Rankinen, "Upper Bounds for Football Pool Problems
  and Mixed Covering Codes", *Journal of Combinatorial Theory, Series A* 56
  (1991), 84-95.
- DOI: `10.1016/0097-3165(91)90024-B`

A later mixed binary/ternary covering-code table is:

- P. R. J. Ostergard and H. O. Hamalainen, "A New Table of Binary/Ternary
  Mixed Covering Codes", *Designs, Codes and Cryptography* 11 (1997),
  151-178.
- DOI: `10.1023/A:1008228721072`

Keri's dated update log records:

```text
2008.10.22
K3(7,3) >= 11
Proved by computer.
```

The public `11..12` interval has therefore persisted for nearly 18 years.
The upper construction itself dates back 35 years.

## Recent Lower-Bound Work

D. Gijswijt and S. Polak, "Semidefinite lower bounds for covering codes",
`arXiv:2504.01932v2`, reports a semidefinite-programming value `8.5250` for
this cell. Integer rounding gives 9, so it does not improve the table's
historical lower bound 11.

## Novelty Search

The search through 2026-09-06 checked:

- the maintained ternary covering-code table and update log;
- references attached to the `K_3(7,3)` table entry;
- recent q-ary lower-bound literature;
- exact covering-code and ternary covering-code searches by parameter; and
- public code and preprint searches for the explicit fixed core, its
  six-word hole, and the reported completion counts.

No public source was located that states or certifies:

- the four-center residual minimum 6 for any of the eight seven-word
  subcores recorded here;
- the four deletion-orbit representatives and exact eligible-pair counts;
- the fixed-core residual minimum 6;
- the exact eight minimizing triples;
- the four stabilizer classes of those triples;
- the four retained non-isometric six-hole near-cover classes;
- the 30-neighbor exact two-replacement plateau; or
- the diameter-at-most-4 lower bound 17 in this form.

This is a negative literature-search result, not proof that no unpublished or
unindexed work exists. The release claim is limited to the repository's
explicit theorem and does not use priority language stronger than the search
supports.

## Relationship To The Historical Bounds

The project reproduces the upper construction independently, but it does not
claim that reconstruction as new.

The seven-word subcore exclusions, eight-word core theorem, and plateau
classification are project-original scoped results. They do not establish
the historical lower bound 11 and do not change the global interval.

## Licensing And Provenance

The project cites and summarizes historical tables and papers. It does not
redistribute their text, tables, or construction files. The retained 12-word
code was reconstructed independently and is verified from first principles.
Project code and original documentation are MIT licensed.
