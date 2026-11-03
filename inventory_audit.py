"""Reproduce proposal cardinalities from one pinned, public JSON inventory."""
import hashlib
import json
from pathlib import Path
from collections import Counter

INVENTORY = Path(__file__).resolve().parent / "vendor/tasks/coding-harness-evolution/environment/data/split.json"
SOURCE_SHA256 = "5a93c153eb784ac01770f072229c8dbac9a4edaf0405769a8b27eb31e2cfc899"


def audit(raw):
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256
    source = json.loads(raw)
    familiar = {"python", "go", "javascript"}
    dev_p = sorted(x for x in source["polyglot"]["dev"] if x.split("/")[0] in familiar)
    final_p = sorted(source["polyglot"]["heldout"])
    dev_s = sorted(source["swe"]["dev"])
    final_s = sorted(source["swe"]["heldout"])
    for rows in (dev_p, final_p, dev_s, final_s):
        assert len(rows) == len(set(rows))
    assert len(dev_p) == 21 and len(final_p) == 40
    assert len(dev_s) == len(final_s) == 20
    assert not set(dev_p) & set(final_p)
    assert not set(dev_s) & set(final_s)
    assert not {x.split("/", 1)[1] for x in dev_p} & {x.split("/", 1)[1] for x in final_p}
    assert not set(dev_p + final_p) & set(source["exclude"])
    assert not {x.split("/", 1)[1] for x in dev_p + final_p} & set(source["polyglot"]["drop_slugs"])
    repo = lambda task: source["swe"]["tasks"][task]["repo"]
    dev_repos = Counter(repo(x) for x in dev_s)
    final_repos = Counter(repo(x) for x in final_s)
    assert not set(dev_repos) & set(final_repos)
    assert len(dev_repos) == len(final_repos) == 4
    assert set(dev_repos.values()) == set(final_repos.values()) == {5}
    return {
        "status": "passed_static_inventory_only",
        "source_raw_sha256": SOURCE_SHA256,
        "development_count": len(dev_p) + len(dev_s),
        "final_count": len(final_p) + len(final_s),
        "development_languages": dict(Counter(x.split("/")[0] for x in dev_p)),
        "final_languages": dict(Counter(x.split("/")[0] for x in final_p)),
        "development_repositories": dict(dev_repos),
        "final_repositories": dict(final_repos),
        "development_ids": ["polyglot/" + x for x in dev_p] + ["swe/" + x for x in dev_s],
        "final_ids": ["polyglot/" + x for x in final_p] + ["swe/" + x for x in final_s],
        "live_gold_and_empty_patch_validation": "pending",
    }


if __name__ == "__main__":
    print(json.dumps(audit(INVENTORY.read_bytes()), indent=2))
