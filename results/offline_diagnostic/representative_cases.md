# Representative saved cases

These are compact adaptations of independently generated follow-up traces.
Data context and upstream attribution: [../../upstream/README.md](../../upstream/README.md).
Full transcripts are not redistributed; step identifiers refer to the recorded controlled evaluation.

| Task / arm | Observed sequence | What it supports |
|---|---|---|
| 5590 / inherit | Product open 3; red 4; X-large 5; Back to Search 6; searches until 10 | Correct ASIN by mate's reward-1 purchase; option application in this trace remains unconfirmed |
| 5590 / reset | Same ASIN open 7; red 8; X-large 9; Buy Now 10; reward 1 | Unchanged option text can accompany eventually confirmed selections |
| 178 / reset | Features 3; unavailable Buy Now 4; return 5; reopen 7; options 8–9; leave 10 | Purchase-control availability and selection uncertainty interact |
| 4819 / inherit | Features 7; unavailable Buy Now 8–9; unchanged page | Attempts are not completed purchases |
| 4819 / reset | Product open 8; required options 9–10; cap | Plausible progress censored; no extra-round success prediction |
| 59 / reset | Product open 8; required options 9–10; cap | Late inspection leaves no observed purchase |
| 5754 / both | Predominantly searches; no product page opened | Shared discovery-floor example |

On task 5590, inherit step 6 says: “The selected variant is not visibly confirmed,
and the page still doesn’t show whether red and x-large are actually applied.”
It returns to search. Reset's step-10 Thought likewise says it should not buy yet,
but its Action clicks Buy Now. The purchase summary confirms red/X-large and
reward 1. This is not a clean intentional ordering-based explanation.

All 14 genuine option clicks leave observation text unchanged. Three values are
later purchase-confirmed: task 2395 size c and task 5590 red/X-large.
The other eleven values lack terminal confirmation.

The older “likely option” heuristic included four product-title clicks and one
color-header click. The corrected audit excludes those five events.

Thoughts are descriptive evidence, not proof that any memory rule caused an action.
Class-compatible/plausible labels do not establish every gold constraint.
