"""Reference aggregation and cutoff selection for trusted evaluator records.

This is preparation code, not a sandbox or runnable benchmark. Candidate code
must never supply the records consumed here. The task adapter must additionally
verify artifact hashes, broker accounting, test integrity, and run provenance.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from statistics import mean


class Unscored(ValueError):
    """The records do not constitute one complete, comparable evaluation."""


def aggregate(protocol: dict, split: str, attempts: list[dict]) -> dict:
    """Require every task/budget/seed exactly once; macro-average fixed groups.

    Each attempt has task_id, regime, seed, status ('pass' or 'fail'). Other
    statuses, including infrastructure_error and invalid, invalidate the whole
    evaluation. Budget exhaustion is metadata; trusted tests decide pass/fail.
    """
    if split not in ("development", "final"):
        raise Unscored("Unknown split")
    tasks = {task["id"]: task for task in protocol[split]}
    regimes = set(protocol["regimes"])
    seeds = set(protocol["seeds"][split])
    expected = {(task_id, regime, seed)
                for task_id in tasks for regime in regimes for seed in seeds}
    seen = set()
    buckets = defaultdict(list)
    for attempt in attempts:
        try:
            key = (attempt["task_id"], attempt["regime"], attempt["seed"])
            if type(attempt["seed"]) is not int or key not in expected:
                raise Unscored("Unexpected task, regime, or seed")
            if key in seen:
                raise Unscored("Duplicate attempt; retries need a separate evaluation record")
            if attempt["status"] not in ("pass", "fail"):
                raise Unscored("Invalid or incomplete attempt: " + str(attempt["status"]))
            task = tasks[attempt["task_id"]]
            subgroup = task.get("repository") if task["group"] == "repository" else task["language"]
            buckets[(attempt["regime"], task["group"], subgroup)].append(
                int(attempt["status"] == "pass")
            )
            seen.add(key)
        except (KeyError, TypeError) as exc:
            raise Unscored("Malformed attempt record") from exc
    if seen != expected:
        raise Unscored(f"Incomplete evaluation: {len(seen)}/{len(expected)} attempts")
    groups = defaultdict(list)
    subgroup_scores = {}
    for (regime, group, subgroup), values in sorted(buckets.items()):
        score = mean(values)
        groups[(regime, group)].append(score)
        subgroup_scores[f"{regime}/{group}/{subgroup}"] = score
    group_scores = {f"{regime}/{group}": mean(values)
                    for (regime, group), values in sorted(groups.items())}
    return {"status": "complete", "split": split, "attempt_count": len(seen),
            "score": mean(group_scores.values()), "groups": group_scores,
            "subgroups": subgroup_scores}


def validate_event(event: dict) -> None:
    """Check the summary schema, not the authenticity of its evidence."""
    required = {"evaluation_id", "artifact_sha256", "protocol_sha256", "split",
                "status", "completed_elapsed_seconds", "score"}
    if not required <= event.keys():
        raise ValueError("Evaluation event is missing required fields")
    if not isinstance(event["evaluation_id"], str) or not event["evaluation_id"]:
        raise ValueError("Invalid evaluation ID")
    for field in ("artifact_sha256", "protocol_sha256"):
        if not isinstance(event[field], str) or not re.fullmatch(r"[0-9a-f]{64}", event[field]):
            raise ValueError("Invalid " + field)
    elapsed = event["completed_elapsed_seconds"]
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError("Invalid elapsed wall time")
    if event["split"] not in ("development", "final"):
        raise ValueError("Unknown event split")
    if event["status"] == "complete":
        score = event["score"]
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Invalid complete score")
    elif event["status"] in ("invalid", "infrastructure_error", "incomplete", "debug"):
        if event["score"] is not None:
            raise ValueError("Unscored events must have null scores")
    else:
        raise ValueError("Unknown evaluation status")


def eligible_events(baseline: dict, events: list[dict], cutoff_hours: float) -> list[dict]:
    """Filter complete development results by completion time, never start time."""
    validate_event(baseline)
    if (baseline["split"] != "development" or baseline["status"] != "complete"
            or baseline["completed_elapsed_seconds"] != 0):
        raise ValueError("A validated development baseline at hour zero is required")
    if not math.isfinite(cutoff_hours) or cutoff_hours <= 0:
        raise ValueError("Invalid cutoff")
    ids = {baseline["evaluation_id"]}
    eligible = [baseline]
    for event in events:
        validate_event(event)
        if event["evaluation_id"] in ids:
            raise ValueError("Duplicate evaluation ID")
        ids.add(event["evaluation_id"])
        if event["protocol_sha256"] != baseline["protocol_sha256"]:
            raise ValueError("Cannot mix protocol revisions")
        if (event["split"] == "development" and event["status"] == "complete"
                and event["completed_elapsed_seconds"] <= cutoff_hours * 3600):
            eligible.append(event)
    return sorted(eligible, key=lambda event: (event["completed_elapsed_seconds"], event["evaluation_id"]))


def select_checkpoint(baseline: dict, events: list[dict], cutoff_hours: float) -> dict:
    eligible = eligible_events(baseline, events, cutoff_hours)
    # Start with baseline explicitly so exact hour-zero ties retain it too.
    best = baseline
    for event in eligible:
        if event["score"] > best["score"]:
            best = event
    return {"cutoff_hours": cutoff_hours, "selection_metric": "development",
            "evaluation_id": best["evaluation_id"], "artifact_sha256": best["artifact_sha256"],
            "protocol_sha256": best["protocol_sha256"], "score": best["score"],
            "completed_elapsed_seconds": best["completed_elapsed_seconds"]}
