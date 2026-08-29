# Vacuum plan — sharh-al-masail-ghulam-hussain

Generated: 2026-08-29 (dry run, no files touched)

## Scope

Five loose NotebookLM-titled recordings in `m4a/` need to (1) be content-matched to
the correct chapter/episode and (2) move into `m4a/Episodes/` under this book's
canonical flat naming (book has 5 episodes, under the 8-episode session threshold,
so no `Session N` subfolder — confirmed against the shipped flat books
`ayyuhal-walad` and `spiritual-ethos`, whose `m4a/Episodes/` files are named
`EP-NN-<Title Case Episode Title>.m4a`).

## Content-match evidence (not filename guesswork)

| Recording | Chapter contract title | Chapter text evidence | Verdict |
|---|---|---|---|
| `Worship_at_the_Market_and_Table.m4a` | ch01 — Lawful Earning and the Table | Opens: "the market stall, the dinner table, and the block where the animal is slaughtered... earning a lawful living is... a form of devotion" | ch01 / EP01 |
| `Uncaught_Fish_and_Righteous_Trade.m4a` | ch02 — Sale, Debt, and the Trust | Opens: "Why would a book of religion care whether you sold a fish that was still swimming?... Nor fish still in the water" (invalid-sale rulings) | ch02 / EP02 |
| `Securing_pledges_shared_walls_and_marriage.m4a` | ch03 — Pledge, Shared Wall, and Marriage | Near-verbatim title match; text: "the pledge held in the hand without a document is the very form the sacred law condemns... the law of the shared wall... the case for marriage" | ch03 / EP03 |
| `The_Fixed_Architecture_of_Family_Bonds.m4a` | ch04 — The Marriage Contract and Its Bonds | "a marriage is built out of bonds nobody chooses" (milk-kinship, mahram rulings, marital rights and duties) | ch04 / EP04 |
| `What_a_Missing_Husband_Still_Owes.m4a` | ch05 — Maintenance, Dissolution, and Inheritance | Opens: "What is a woman supposed to do when her husband simply stops existing?... a missing husband has left her without maintenance" | ch05 / EP05 |

All five matches are unambiguous — each recording's opening lines and worked
examples correspond to only one chapter's subject matter. No `VAC-PAIRING-AMBIGUOUS`
findings.

## Proposed mutations (severity: safe — move + rename, no deletes)

| Before | After |
|---|---|
| `m4a/Worship_at_the_Market_and_Table.m4a` | `m4a/Episodes/EP-01-Earning and the Manners of the Table.m4a` |
| `m4a/Uncaught_Fish_and_Righteous_Trade.m4a` | `m4a/Episodes/EP-02-Sale, Debt, and the Contracts of Trade.m4a` |
| `m4a/Securing_pledges_shared_walls_and_marriage.m4a` | `m4a/Episodes/EP-03-The Pledge and the Call to Marry.m4a` |
| `m4a/The_Fixed_Architecture_of_Family_Bonds.m4a` | `m4a/Episodes/EP-04-The Marriage Contract and Its Bonds.m4a` |
| `m4a/What_a_Missing_Husband_Still_Owes.m4a` | `m4a/Episodes/EP-05-Maintenance, Dissolution, and Inheritance.m4a` |

Reason: NotebookLM assigns its own topical titles on export; canonical naming
matches the book's `EP0N-*` episode-framing slugs, title-cased with spaces, in the
`EP-NN-<Title>.m4a` shape already used by shipped flat books in this bucket.

No transcripts exist yet for these recordings (`m4a/transcripts/` is empty/absent),
so no transcript renames are proposed in this pass.

## Not proposed

- No `Session N` subfolder — this book is flat by the 8-episode threshold rule.
- No deletes, no archive moves — this is a pure rename+move pass.
