# Source and data provenance

This task adapts existing code and public task data. Publication under a contributor-owned repository does not make those components original work.

## Vendored implementation

The files under `vendor/tasks/coding-harness-evolution/` are copied byte for byte from [Scale's RSI-Bench coding-harness-evolution task](https://github.com/scaleapi/rsi-benchmark/tree/034aa5bdbce45f38da0634980c27186e2272c6ea/tasks/coding-harness-evolution) at commit `034aa5bdbce45f38da0634980c27186e2272c6ea`. The task credits Zhaotian Weng and Jenny Zhang. Copyright and MIT terms are preserved in [vendor/LICENSE](vendor/LICENSE); per-file notices and canaries are unchanged. `vendor-manifest.json` records the original Git blob SHA-1 for each file. These files are reference source, not a newly implemented evaluator.

The source baseline is the four-file DGM-style coding harness in `environment/baseline/harness/`. Its previously reported reward belongs to the original protocol and is not a result for this task. Any local-model transport adaptation must be published as a diff and applied equally to the baseline and candidate harnesses.

## Public assets

- Aider Polyglot: commit `7e0611e77b54e2dea774cdc0aa00cf9f7ed6144f`; retain its and the underlying Exercism exercises' license notices.
- SWE-bench Pro task files: commit `66f92766bba642462d4bbe5479e83f91f9211862`; dataset revision `2d52cb3df914a3fcf80c7f66738b3a88ae37fc50`. Retain individual repository and dataset licenses.
- Qwen/Qwen3-Coder-30B-A3B-Instruct model and tokenizer: revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`. Weights are not redistributed here.
- OpenRSI integration was inspected at commit `eca7d9e4857900ef8485a1f2137eb51bdc2dcc33`.

The original source inventory's raw SHA-256 is `5a93c153eb784ac01770f072229c8dbac9a4edaf0405769a8b27eb31e2cfc899`. The formatted `source-split.json` is parsed-content equivalent; the vendored copy preserves original bytes. Inventory auditing establishes counts and exclusions, not successful gold/empty-patch execution or absence of pretraining contamination.

## Task-owned preparation

The root-level protocol, strict aggregation, checkpoint selection, inventory checks, and plotting tools support the new two-budget transfer evaluation. They are preparation artifacts and do not replace live serving, isolation, task construction, or matched-baseline validation. No claim of a completed experiment or universal coding generalization is made.
