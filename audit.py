"""Read-only source/protocol audit. Does not execute benchmark or model code."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    source = json.loads((root / "source-split.json").read_text())
    protocol = json.loads((root / "protocol.json").read_text())
    dev, final = protocol["development"], protocol["final"]
    checks = {}

    def check(name, value):
        checks[name] = bool(value)

    for split_name, rows, upstream in (("development", dev, "dev"), ("final", final, "heldout")):
        ids = [row["id"] for row in rows]
        check(split_name + "_unique_ids", len(ids) == len(set(ids)))
        source_ids = {"polyglot/" + x for x in source["polyglot"][upstream]}
        source_ids |= {"swe/" + x for x in source["swe"][upstream]}
        check(split_name + "_present_in_upstream", set(ids) <= source_ids)
        check(split_name + "_honors_source_exclusions", not ({x.removeprefix("polyglot/") for x in ids if x.startswith("polyglot/")} & set(source["exclude"])))

    check("development_count_41", len(dev) == 41)
    check("final_count_60", len(final) == 60)
    check("no_id_overlap", not ({r["id"] for r in dev} & {r["id"] for r in final}))
    dev_slugs = {r["id"].split("/")[-1] for r in dev if r["kind"] == "polyglot"}
    final_slugs = {r["id"].split("/")[-1] for r in final if r["kind"] == "polyglot"}
    check("no_exercise_semantic_slug_overlap", not (dev_slugs & final_slugs))
    dev_repos = {r["repository"] for r in dev if r["kind"] == "swe"}
    final_repos = {r["repository"] for r in final if r["kind"] == "swe"}
    check("repository_disjoint", not (dev_repos & final_repos))
    check("four_repositories_per_split", len(dev_repos) == len(final_repos) == 4)
    check("development_languages", {r["language"] for r in dev if r["kind"] == "polyglot"} == {"python", "go", "javascript"})
    check("unseen_languages_absent_from_development", not any(r["language"] in {"cpp", "java", "rust"} for r in dev))
    check("final_groups", Counter(r["group"] for r in final) == {"familiar_language": 21, "unseen_language": 19, "repository": 20})
    # pilot_passed records the upstream agent pilot, not gold-patch validity.
    # Gold/empty-patch validity is a required live image-build check, not a
    # property that can be inferred from this metadata audit.
    result = {
        "status": "passed" if all(checks.values()) else "failed",
        "scope": "static metadata and provenance only; upstream pilot claims are not independently reproduced",
        "checks": checks,
        "source_commit": protocol["source_commit"],
        "source_split_sha256": hashlib.sha256((root / "source-split.json").read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256((root / "protocol.json").read_bytes()).hexdigest(),
        "reference_harness_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root / "vendor/tasks/coding-harness-evolution/environment/baseline/harness").glob("*.py"))},
        "development_tasks": len(dev),
        "final_tasks": len(final),
        "development_attempts_per_full_candidate": len(dev) * len(protocol["regimes"]) * protocol["development_repeats"],
        "final_attempts_per_frozen_artifact": len(final) * len(protocol["regimes"]) * protocol["final_repeats"],
        "executed_model_calls": 0,
        "executed_benchmark_attempts": 0,
        "pending_live_checks": ["all gold patches and reference solutions pass", "all empty patches and stubs fail", "serving and isolation", "matched baseline", "full evaluation runtime"],
    }
    print(json.dumps(result, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
