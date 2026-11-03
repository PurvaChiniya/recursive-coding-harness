"""Synthetic contract tests only; these are not benchmark measurements."""
import json
import tempfile
import unittest
from pathlib import Path

from evaluation_contract import Unscored, aggregate, select_checkpoint
from plot_evolution import render

PROTOCOL = json.loads(Path(__file__).with_name("protocol.json").read_text())


def attempts(split="final", passed=lambda task: False):
    return [{"task_id": task["id"], "regime": regime, "seed": seed,
             "status": "pass" if passed(task) else "fail"}
            for task in PROTOCOL[split] for regime in PROTOCOL["regimes"]
            for seed in PROTOCOL["seeds"][split]]


def event(name, hour, score, **extra):
    result = {"evaluation_id": name, "artifact_sha256": "a" * 64,
              "protocol_sha256": "b" * 64, "split": "development",
              "status": "complete", "completed_elapsed_seconds": hour * 3600,
              "score": score}
    result.update(extra)
    return result


class AggregationTests(unittest.TestCase):
    def test_all_pass_and_all_fail(self):
        for split in ("development", "final"):
            self.assertEqual(aggregate(PROTOCOL, split, attempts(split))["score"], 0)
            self.assertEqual(aggregate(PROTOCOL, split, attempts(split, lambda _: True))["score"], 1)

    def test_unequal_language_counts_use_macro_average(self):
        # Java has 7 tasks, C++ and Rust each 6. Java alone passing contributes
        # exactly 1/3 of the unseen-language group and 1/9 of the final score.
        report = aggregate(PROTOCOL, "final", attempts(passed=lambda t: t["language"] == "java"))
        self.assertAlmostEqual(report["score"], 1 / 9)
        self.assertEqual(report["attempt_count"], 360)

    def test_repository_and_budget_weights(self):
        rows = attempts("development", lambda t: t.get("repository") == "ansible/ansible")
        for row in rows:
            if row["regime"] == "tight":
                row["status"] = "fail"
        # One of four repositories, in one of two groups, in one of two budgets.
        self.assertAlmostEqual(aggregate(PROTOCOL, "development", rows)["score"], 1 / 16)

    def test_missing_duplicate_and_unexpected_attempts_are_unscored(self):
        rows = attempts()
        for invalid in (rows[:-1], rows + [rows[0]], rows + [dict(rows[0], seed=99)]):
            with self.assertRaises(Unscored):
                aggregate(PROTOCOL, "final", invalid)

    def test_infrastructure_and_candidate_invalid_are_unscored(self):
        for status in ("infrastructure_error", "invalid", "incomplete"):
            rows = attempts()
            rows[0]["status"] = status
            with self.assertRaises(Unscored):
                aggregate(PROTOCOL, "final", rows)

    def test_budget_exhaustion_uses_trusted_grade(self):
        rows = attempts("development", lambda _: True)
        rows[0]["budget_exhausted"] = True
        self.assertEqual(aggregate(PROTOCOL, "development", rows)["score"], 1)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.baseline = event("baseline", 0, .4)

    def test_cutoffs_use_completed_development_only(self):
        rows = [event("before", 11, .5), event("late", 12.001, .8),
                event("final", 4, 1, split="final"),
                event("debug", 5, None, status="debug")]
        self.assertEqual(select_checkpoint(self.baseline, rows, 12)["evaluation_id"], "before")
        self.assertEqual(select_checkpoint(self.baseline, rows, 24)["evaluation_id"], "late")

    def test_exact_cutoff_included_and_ties_keep_earliest(self):
        rows = [event("at_cutoff", 12, .6), event("earlier", 11, .6)]
        self.assertEqual(select_checkpoint(self.baseline, rows, 12)["evaluation_id"], "earlier")
        self.assertEqual(select_checkpoint(self.baseline, rows[:1], 12)["evaluation_id"], "at_cutoff")

    def test_baseline_remains_incumbent_when_candidates_regress(self):
        self.assertEqual(select_checkpoint(self.baseline, [event("worse", 2, .3)], 12)["evaluation_id"], "baseline")

    def test_duplicate_mixed_protocol_and_nonfinite_rejected(self):
        cases = [[event("baseline", 1, .9)],
                 [event("different", 1, .9, protocol_sha256="c" * 64)],
                 [event("nan", 1, float("nan"))],
                 [event("infra", 1, 0, status="infrastructure_error")]]
        for rows in cases:
            with self.assertRaises(ValueError):
                select_checkpoint(self.baseline, rows, 12)


class PlotTests(unittest.TestCase):
    def test_incomplete_run_cannot_make_full_window_figures(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                render({"status": "completed", "elapsed_seconds": 12 * 3600}, Path(tmp))
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_two_figures_use_expected_checkpoint_selections(self):
        # Exercise rendering in a temporary directory. Never retain synthetic
        # plots among submission evidence or describe them as measured results.
        run = {"status": "completed", "elapsed_seconds": 24 * 3600,
               "baseline": event("baseline", 0, .4),
               "events": [event("early", 8, .5), event("regression", 10, .3),
                          event("late", 18, .6), event("infra", 20, None, status="infrastructure_error")]}
        with tempfile.TemporaryDirectory() as tmp:
            result = render(run, Path(tmp))
            self.assertEqual(result["checkpoints"]["12"]["evaluation_id"], "early")
            self.assertEqual(result["checkpoints"]["24"]["evaluation_id"], "late")
            for hours in (12, 24):
                self.assertTrue((Path(tmp) / f"evolution_{hours}h.png").read_bytes().startswith(b"\x89PNG"))
                self.assertIn("<svg", (Path(tmp) / f"evolution_{hours}h.svg").read_text())
            with self.assertRaises(ValueError):
                render(run, Path(tmp))


if __name__ == "__main__":
    unittest.main()
