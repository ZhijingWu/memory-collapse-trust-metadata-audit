# Limitations

- One method: ExpeL. Count/vote heuristics are not calibrated confidence.
- One selected real replay state; large count contrast motivated selection.
- One released WebShop 50-task stream and one rollout per memory/task.
- Temperature zero does not imply deterministic model/provider outputs.
- Independent builds diverge before the first EDIT; 15 pair distances are
  dependent because they reuse six builds.
- Token-Jaccard and count-cosine distances do not establish semantic correctness.
  Exact-string overlap is zero across all independent builds; ordering comparison
  is undefined when fewer than two strings are shared.
- The controlled pair changes ordering and induced rule numbering together.
- The severe 10-round floor censors 96/100 episodes. No extra actions were
  simulated and no 15/20-round success is predicted.
- Observation text can hide successful option application. Only three unchanged
  option values have later purchase confirmation; eleven remain unconfirmed.
- Many attempted clicks target controls absent from the current observed page.
  A no-op is not a completed zero-reward purchase.
- Most inspected-product correctness is unverified. Title/class and available
  option labels are conservative proxies; the paired reward-1 result proves only
  task 5590's selected product association.
- Loop heuristics include potentially useful actions and depend on thresholds.
  Full definitions and all exploratory tests are disclosed.
- The original backend transport configuration is excluded for privacy. Paid
  reruns may not reproduce identical outputs; compact offline reaggregation is
  deterministic. Full trace reclassification requires externally retained traces.
- No Level-3 or Level-4 causal claim. No claim of performance improvement or
  that count inheritance explains overall memory collapse.
- Interface repair is a proposed focused diagnostic, not an experiment conducted
  in this artifact.

The public artifact includes one necessary attributed rule-state fixture,
derived token frequencies/hashes, numeric outcomes and brief trace excerpts.
It intentionally omits the full upstream dataset and raw follow-up transcripts.
