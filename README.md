# Trust-Metadata Inheritance in Continually Updated LLM Memory

An independent mechanism-level follow-up to
[*Useful Memories Become Faulty When Continuously Updated by LLMs*](https://arxiv.org/abs/2605.12978).

ExpeL rewrites rule content while retaining accumulated support. In one identical
real pre-EDIT state, resetting that support moves the edited rule from rank 2 to
rank 15 while preserving the complete rule-text set. Independent compression is
highly stochastic, and a controlled 50-task WebShop comparison does not establish
a reliable downstream benefit. Saved trajectories expose a severe discovery,
purchase-control and option-observability bottleneck.

## 1. Overview

This repository contains a minimal patch, reproducible offline analysis, compact
derived tables and a necessary single-state replay fixture. It preserves the
negative/weak downstream result. It does not redistribute the full upstream
repository, task pools or 100 episode transcripts.

## 2. Research Question

When an EDIT replaces a rule, should the new content retain support accumulated
for its previous text? Can that metadata affect solver-visible ordering or
removal resistance, and can those structural effects be distinguished from
consolidation stochasticity and evaluation limitations?

Counts are importance/vote heuristics, not calibrated confidence. Numeric counts
are absent from the solver prompt; ordering and induced numbering are visible.

## 3. Key Findings

| Finding | Recorded evidence | Scope |
|---|---|---|
| EDIT inherits support | inherit assigns old_count + 1; reset assigns ADD_INITIAL_COUNT = 2 | Code semantics |
| Same-state ranking divergence | old count 29; inherit count 30/rank 2; reset count 2/rank 15 | Identical 36-rule text multiset |
| A/A and A/B lexical distances overlap | pooled A/A 0.5732; A/B 0.5735 Token-Jaccard distance | Six builds / 15 dependent comparisons |
| Controlled WebShop benefit unresolved | inherit 0/50; reset 1/50; exact paired p = 1.0 | One rollout per arm/task |
| Severe fixed-budget floor | 96/100 episodes hit the 10-round cap | No extra-round prediction |
| Purchase-control mismatch | 11/15 Buy Now attempts target an unavailable control and leave the page unchanged | Nine episodes / seven tasks |
| Invisible option transitions | 14 genuine option clicks leave text unchanged; three values later purchase-confirmed | Remaining values unconfirmed |

## 4. Mechanism Audit

[The minimal patch](upstream/expel_edit_count.patch) adds the opt-in inherit/reset
policy and EDIT instrumentation: old/new text, old/new count, step, rule index and
edit_change. The last metric is 1 minus unique case-folded word-token Jaccard.
The default inherit policy preserves original behavior. ADD, AGREE, REMOVE,
matching, sorting and prompts are unchanged. Checkpoint policy mismatches are
rejected; event sidecars are reconstructed from checkpoint-backed history.

The focused tests are [here](tests/test_expel_policy.py). They load the separately
obtained patched upstream files and use scripted responses, with no model calls.

## 5. Deterministic Shared-State Replay

[Replay summary](results/mechanism/shared_pre_edit_replay.json) and
[the necessary frozen state](results/mechanism/frozen_pre_edit_state.json)
isolate the count assignment and subsequent stable sort. The selected state is
immediately before the sole EDIT at compression step 43, after that batch's
REMOVE/AGREE operations; a later ADD is excluded.

Both branches contain 36 identical rule texts. Fourteen numbered positions differ.
Repeated same-target REMOVE at strength 3 would require 10 calls for count 30
versus one for count 2, assuming no intervening updates. This is an analytic
removal-resistance diagnostic, not an observed continuation.

## 6. A/A Stochasticity Control

Three independent N=50 builds per policy yield three inherit A/A, three reset A/A
and nine A/B comparisons. All 15 diverge at step 1, before the earliest EDIT at
step 2. A/B final-memory lexical separation does not exceed the A/A baseline.

[Compact lexical features](results/stochasticity/lexical_features.json) retain
token frequencies and sequence/rule hashes rather than six full memory dumps.
[All comparisons](results/stochasticity/pairwise_summary.csv) and
[group summaries](results/stochasticity/summary.json) are reproducible offline.
Pair distances share builds and are not 15 independent observations.
Lexical similarity does not establish semantic correctness.

## 7. Controlled WebShop Evaluation

The two frozen memories have exactly identical content/punctuation and different
count-induced order/numbering. The selected rule is rank 2 versus 15. Both use
gpt-5.4-mini, temperature 0, reasoning none, 1024 output-token cap, the same
released 50-task stream and frozen prices, with a 10-round budget and no memory
updates. Odd stream positions run inherit/reset; even positions reset/inherit.

[Task-pair table](results/controlled_eval/paired_results_summary.csv) and
[summary](results/controlled_eval/summary.json): one reset win, no inherit wins,
no both-success pairs, 49 both-fail pairs; paired difference +2 percentage points;
exact two-sided McNemar/binomial p = 1.0. Mean rewards are 0.0133 and 0.0500.
There were 493 and 487 model calls. This does not establish a reliable downstream
benefit or equivalence between the policies.

## 8. Offline Failure Analysis

[Taxonomy](results/offline_diagnostic/failure_taxonomy.csv),
[100 derived feature rows](results/offline_diagnostic/episode_features.csv),
[paired behavioral summaries](results/offline_diagnostic/behavioral_summary.csv)
and [brief cases](results/offline_diagnostic/representative_cases.md) document
the audit. Classification is rule-based and manually auditable; no LLM classifier
or new environment action was used.

Of 96 capped episodes, 88 end searching and 70 never inspect a class-compatible
product. Loop incidence is 38/50 inherit and 40/50 reset. Reset averages 1.20 more
searches, while inherit has more repeated action strings. None of eight
exploratory paired sign tests survives Holm correction.

The corrected option audit excludes five false positives from an earlier
“likely option” heuristic: four title clicks and one header click. The 11
unavailable purchase attempts are not completed zero-reward purchases.
Thought text is descriptive evidence, not proof that a rule caused an action.

## 9. Interpretation

The study establishes a structural mechanism: support inheritance can change
ranking and removal resistance under fixed content. Downstream benefit remains
unresolved. Evaluation shows strong common workflow/observability limitations;
their causal contribution and the effect of repairing them remain unmeasured.
The evidence level remains 2, with no Level-3/Level-4 causal claim.

A future focused test could add explicit state-preserving feedback for
unavailable clicks. It is a recommendation; no such experiment is included.

## 10. Limitations

One method, one selected replay state, one 50-task stream and one rollout per
memory/task restrict generalization. Temperature zero does not imply deterministic
provider outputs. Most product correctness is unverified; class-compatible titles
are proxies. The cap causes censoring, and observation text can hide state changes.
See [the complete limitations](docs/limitations.md).

## 11. Reproduction

Start with [reproducibility instructions](docs/reproducibility.md).
Offline analysis needs Python 3.10+ and the standard library. The upstream source
and any paid compression/evaluation runtime must be obtained separately.

    python src/stochasticity/analyze.py --features results/stochasticity/lexical_features.json --output-dir work/stochasticity
    python src/controlled_eval/analyze_pairs.py --input results/controlled_eval/paired_results_summary.csv --output work/paired.json
    python src/offline_diagnostic/summarize.py --input results/offline_diagnostic/episode_features.csv --output work/offline.json
    python tools/validate_artifact.py

The replay additionally needs a separately patched upstream rules.py.
Recomputing full trajectory classifications needs externally retained raw traces;
those traces are intentionally not bundled. Paid runners default to a schedule
preview and require an explicit execution flag.

## 12. Repository Structure

- upstream/: minimal patch, attribution and retained MIT notices
- src/replay/: fixed-state replay
- src/stochasticity/: compact-feature export and 15-pair analysis
- src/controlled_eval/: memory equality, paired analysis and opt-in execution
- src/offline_diagnostic/: trajectory classifier and feature reaggregation
- results/: small derived scientific artifacts
- docs/: methodology, limitations, reproduction and provenance
- tests/ and tools/: focused patch tests and artifact/security validation

## 13. Upstream Attribution

Official source: [DylanZSZ/Memory-Collapse-Eval](https://github.com/DylanZSZ/Memory-Collapse-Eval),
pinned to adf347f67a81a19fc71d2529d09108c71a1f9712 for this patch.
The paper is by Dylan Zhang, Yanshan Lin, Zhengkun Wu, Yihang Sun, Bingxuan Li,
Dianqi Li and Hao Peng. The author of this independent follow-up is Zhijing Wu.

Original code is MIT; original released results/data remain CC BY 4.0.
AgentGym is MIT, copyright FudanNLP-Agent. Attribution and scope are in
[upstream/README.md](upstream/README.md). Obtain original datasets from the
official source; benchmark licenses and provider output terms remain applicable.

## 14. Citation

[CITATION.cff](CITATION.cff) identifies this artifact and references the paper.
Please credit both when using the follow-up in the upstream study's context.

Zhijing Wu. Trust-Metadata Inheritance in Continually Updated LLM Memory:
A Mechanism-Level Audit of ExpeL. 2026.
