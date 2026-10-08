# Reproducibility

All public analysis uses Python 3.10+ and the standard library. No analysis
command below calls a model or interacts with WebShop. Optional PyYAML can parse
CITATION.cff during validation if already installed; it is not required.

Run commands from this artifact's root. Put generated/private work under work/,
which is ignored. Never commit credentials or raw operational logs.

## A. Offline mechanism and derived-result analysis

Obtain the official repository separately and pin the patch base:

    git clone https://github.com/DylanZSZ/Memory-Collapse-Eval.git work/upstream-source
    git -C work/upstream-source checkout adf347f67a81a19fc71d2529d09108c71a1f9712
    git -C work/upstream-source apply --check ../../upstream/expel_edit_count.patch
    git -C work/upstream-source apply ../../upstream/expel_edit_count.patch

These commands change the separately obtained clone. They do not require a copy
of upstream to be distributed in this artifact.

    PYTHONDONTWRITEBYTECODE=1 AUDIT_UPSTREAM=work/upstream-source python tests/test_expel_policy.py -v
    python src/replay/replay.py --state results/mechanism/frozen_pre_edit_state.json --rules-file work/upstream-source/agentgym/agentenv/agentenv/memory/methods/expel/rules.py --output work/replay.json --memory-dir work/memories
    python src/controlled_eval/check_memories.py --inherit work/memories/inherit.txt --reset work/memories/reset.txt
    python src/stochasticity/analyze.py --features results/stochasticity/lexical_features.json --output-dir work/stochasticity
    python src/controlled_eval/analyze_pairs.py --input results/controlled_eval/paired_results_summary.csv --output work/paired.json
    python src/offline_diagnostic/summarize.py --input results/offline_diagnostic/episode_features.csv --output work/offline.json
    python tools/validate_artifact.py

Expected replay: old count 29, inherit 30/rank 2, reset 2/rank 15, 36 rules and
identical text multisets. The compact lexical features reproduce the 15-pair
distances without six complete memory dumps. Pair statistics reproduce 0/50
versus 1/50 and exact p=1.0; feature reaggregation reproduces the disclosed
eight-feature exploratory sign/Holm analysis.

Full classification needs externally retained raw episode audits/conversations,
not just the derived feature table:

    python src/offline_diagnostic/analyze.py --input-dir work/full-evaluation --inherit-memory work/memories/inherit.txt --reset-memory work/memories/reset.txt --output-dir work/full-offline-diagnostic

The input layout is episodes/01/inherit/ etc., with completion.json,
action_audit.jsonl, response_audit.jsonl, prompt_audit.jsonl and conversations/.
The evaluation root contains manifest.json, execution_order.jsonl,
paired_results.jsonl and results_summary.json. The opt-in runner below produces
this layout. The original raw follow-up traces are not bundled; complete
classification cannot be independently checked from summaries alone.

## B. Independently reproduce compression (paid, opt-in)

Obtain the original N=50 pool and gold pool from the official upstream release:

- results/webshop_retrieval-hijack/pools/gpt5.4mini/pool_armC_N50.jsonl
- results/webshop_retrieval-hijack/pools/gold_train.jsonl

Use upstream's matching client runtime and the patched implementation.
Configure credentials privately; placeholders are deliberately not real values:

    export OPENAI_API_KEY=...
    export OPENAI_BASE_URL=...
    export PYTHONPATH="$PWD/work/upstream-source/agentgym/agentenv"
    export SCIWORLD_SYS_PROMPT=""
    export SCIWORLD_REASONING_EFFORT=none

For each policy, use a fresh output directory:

    python work/upstream-source/agentgym/agentenv/scripts/memory/compress.py --env webshop --method expel --pool work/upstream-source/results/webshop_retrieval-hijack/pools/gpt5.4mini/pool_armC_N50.jsonl --gold-pool work/upstream-source/results/webshop_retrieval-hijack/pools/gold_train.jsonl --method-config configs/inherit.json --memory-out work/builds/n50_inherit/mem.txt --llm-model gpt-5.4-mini --llm-max-tokens 16384 --llm-temperature 0 --llm-extra-body '{}'
    python work/upstream-source/agentgym/agentenv/scripts/memory/compress.py --env webshop --method expel --pool work/upstream-source/results/webshop_retrieval-hijack/pools/gpt5.4mini/pool_armC_N50.jsonl --gold-pool work/upstream-source/results/webshop_retrieval-hijack/pools/gold_train.jsonl --method-config configs/reset.json --memory-out work/builds/n50_reset/mem.txt --llm-model gpt-5.4-mini --llm-max-tokens 16384 --llm-temperature 0 --llm-extra-body '{}'

Settings: max_num_rules 20, success_chunk_size 8, rounds 1, original chunk seed
42, no trajectory recollection or prompt changes. The selected pool scheduled
43 calls per build. Repeat independently into inherit_rep2/inherit_rep3 and
reset_rep2/reset_rep3 to obtain three builds per policy. These are reproduction
instructions, not experiments executed by this release workflow.

    python src/stochasticity/export_features.py --runs-root work/builds --output work/lexical_features.json
    python src/stochasticity/analyze.py --features work/lexical_features.json --output-dir work/new-stochasticity

Temperature zero does not promise byte-identical new builds. The recorded
results are observations, not guaranteed outcomes of a fresh paid reproduction.
API endpoint, credential, proxy and transport configuration are intentionally
excluded from the release.

## C. Controlled frozen-price WebShop evaluation (paid, opt-in)

Obtain these from upstream, under their own licenses:

- results/webshop_retrieval-hijack/tasks/streams/eval_stream.json
- env/webshop/product_prices.json and env/webshop/indexes_1k/
- agentgym/agentenv-webshop/ runtime source and documented product data

Follow upstream docs/running.md and the documented WebShop setup order. The
original study used an isolated Python 3.8 server, shipped index (no rebuild),
frozen prices and typing_extensions<4.6.0 pinned last. Compatibility required
Altair 5.0.1 with that typing cap. The evaluation client used OpenAI SDK 1.109.1.
These are relevant compatibility settings, not a redistributed environment.

Before server startup, set:

    export WEBSHOP_FROZEN_PRICES="$PWD/work/upstream-source/env/webshop/product_prices.json"

Start the matching server according to upstream documentation and supply its
URL through your own WEBSHOP_ENV_URL variable. Setting frozen prices only in the
evaluation client does not freeze an already-running server. Verify matching
task identities, frozen prices and server health before paid execution.

Construct the two memories with the shared-state replay in A. Preview the
counterbalanced schedule without model/environment calls:

    python src/controlled_eval/run_pairs.py --upstream work/upstream-source --stream work/upstream-source/results/webshop_retrieval-hijack/tasks/streams/eval_stream.json --inherit-memory work/memories/inherit.txt --reset-memory work/memories/reset.txt --env-url "$WEBSHOP_ENV_URL" --output-dir work/full-evaluation

Only adding --execute permits paid calls. Keep the same client Python, model,
decoding, 10-round budget and fixed server in both arms. Run durably using your
preferred terminal/session manager. The runner alternates arm order, saves every
completed episode and skips completed episodes. Incomplete episodes are retained
and stop automatic resume; inspect them rather than restarting blindly.

The audited episode wrapper verifies frozen memory headers and the no-op memory
end hook, records action/response audits, and retries a failed connection request
at most three times with 2/4/8-second backoff. It does not persist credential
values or provider URLs. Server provisioning and frozen-state monitoring are the
reproducer's responsibility; do not switch environments to bypass a failure.

Maximum scheduled model turns: 50 tasks × 2 arms × 10 rounds = 1000; observed
total was 980. Inspect raw results privately, then publish only sanitized derived
summaries under appropriate attribution. No replaying extra rounds is implied.
