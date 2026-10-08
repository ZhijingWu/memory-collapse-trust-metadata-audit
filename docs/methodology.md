# Methodology and the reason for each control

1. **Audit the implementation.** A rule is text plus an integer importance count.
   EDIT replaces text and adds one to existing support. Stable count-descending
   sorting exposes that support through ordering; counts themselves are omitted
   from solver text. Removal resistance is a second structural channel.
2. **Make a minimal intervention.** inherit retains old_count + 1; reset uses the
   ADD initial value 2. Keep ADD/AGREE/REMOVE, prompts and matching unchanged.
   Log actual applied EDITs; redirected EDIT-to-AGREE is outside the intervention.
3. **Run the smallest N=50 pilot.** Use the same released pool, gold references,
   model/settings and chunk seed 42. Each compression uses 43 scheduled calls;
   max_num_rules=20, success_chunk_size=8, rounds=1. max_num_rules is a prompt/
   removal-pressure threshold, not a hard top-k truncation.
4. **Notice pre-EDIT divergence.** Different independent builds already diverge
   before an EDIT. A fresh inherit/reset difference mixes the count intervention
   with model/provider stochasticity.
5. **Add A/A controls.** Three independent builds per policy create all 15 pair
   comparisons. Final-memory lexical distances overlap across within/cross-policy
   comparisons. Count dynamics differ, but lexical change is not semantic harm.
6. **Freeze a real shared state.** Reconstruct immediately before the sole EDIT
   at the original inherit build's final step. Earlier same-batch REMOVE/AGREE
   effects are included; the subsequent ADD is excluded. The reconstruction is
   supported by the applied event, step snapshots and checkpoint counts.
7. **Construct an identical-content control.** Apply only that recorded EDIT to
   the same 36-rule state under both policies. Content is byte-equivalent as an
   unordered multiset; count 30 versus 2 moves the rule from rank 2 to 15. Render
   every rule with the same WebShop ExpeL framing and no visible counts.
8. **Evaluate frozen matched tasks.** Both memories use the same released ordered
   50-task stream and frozen prices. Counterbalance which arm goes first by
   stream position. Save each completed episode; no memory consolidation occurs.
   The primary binary comparison is exact McNemar/binomial on discordant pairs.
9. **Diagnose the floor offline.** With 96 cap hits and one binary reversal,
   inspect actual actions/states instead of overinterpreting success. Distinguish
   purchase attempts, control availability, actual termination and selected
   values later confirmed by a purchase. Use explicit loop/classification rules,
   matched-task sign tests and an eight-feature Holm-corrected exploratory family.

## What the controls isolate

Shared-state replay isolates count assignment followed by ordering/pruning
mechanics. Controlled evaluation holds rule content fixed but changes order and
induced numbered positions together. It does not isolate ordering from numbering,
remove provider stochasticity, or establish effects across all memory methods.

The single selected state was chosen for a large recorded count/lexical-change
contrast; it is not a random sample of EDITs. The original trust-metadata
hypothesis concerns inherited importance, not calibrated confidence or semantic
version tracking. Reset also removes the immediate EDIT increment, so inherited
support and that increment are not separately estimated.

Offline primary categories are mutually exclusive observable signatures, not
causal shares. Informational inspection progress can occur on an ultimately
wrong candidate. Thought text is supporting description only.
