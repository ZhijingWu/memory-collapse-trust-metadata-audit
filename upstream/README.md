# Upstream attribution and scope

This artifact is an independent follow-up study by Zhijing Wu. It is based on
[Memory-Collapse-Eval](https://github.com/DylanZSZ/Memory-Collapse-Eval) and the paper
[Useful Memories Become Faulty When Continuously Updated by LLMs](https://arxiv.org/abs/2605.12978),
by Dylan Zhang, Yanshan Lin, Zhengkun Wu, Yihang Sun, Bingxuan Li, Dianqi Li and
Hao Peng. This artifact does not imply authorship of that paper.

The patch is against upstream commit adf347f67a81a19fc71d2529d09108c71a1f9712.
It touches only the ExpeL rules.py and core.py. The full implementation is not
copied; obtain the original repository separately.

Original repository code is MIT: retained notice [LICENSE-MEMORY-COLLAPSE](LICENSE-MEMORY-COLLAPSE).
The vendored AgentGym component is also MIT, copyright (c) 2023 FudanNLP-Agent:
retained notice [LICENSE-AGENTGYM](LICENSE-AGENTGYM). Upstream's NOTICE confirms
that third-party components retain their own terms.

Original released results/data are **CC BY 4.0**. These terms are not replaced by
this artifact's code license. See [the upstream data license](https://github.com/DylanZSZ/Memory-Collapse-Eval/blob/adf347f67a81a19fc71d2529d09108c71a1f9712/LICENSE-DATA)
and [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

This repository does not redistribute the full upstream dataset. It publishes
small adaptations: a necessary selected rule-state replay fixture, derived
token counts/hashes, outcome/features tables and brief independently generated
follow-up case excerpts. Changes include the count-policy intervention,
independent recompression, shared-state reconstruction, controlled paired
evaluation and rule-based diagnostics. Sources and transformations are described
in [provenance](../docs/provenance.json).

Obtain original pools, gold references, task stream, frozen price table and
benchmark runtime from the official source. CC BY 4.0 does not relicense
underlying benchmark data or override model-provider output terms.
