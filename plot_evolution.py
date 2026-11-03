"""Render measured 12h/24h development curves from trusted run summaries.

Usage: python3 plot_evolution.py --run RUN.json --output OUTPUT_DIR
Input schema and current limitations are documented in README.md.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from evaluation_contract import eligible_events, select_checkpoint


def render(run: dict, output: Path) -> dict:
    elapsed = run.get("elapsed_seconds")
    if (type(elapsed) not in (int, float) or not math.isfinite(elapsed)
            or elapsed < 24 * 3600 or run.get("status") != "completed"):
        raise ValueError("Two complete-window figures require a completed 24-hour run")
    baseline, events = run["baseline"], run["events"]
    # Validate everything before creating output, and reject impossible timing.
    eligible_events(baseline, events, 24)
    if any(e["completed_elapsed_seconds"] > elapsed for e in events):
        raise ValueError("An evaluation completed after the recorded run duration")
    selections = {str(hours): select_checkpoint(baseline, events, hours) for hours in (12, 24)}
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be empty; preserve earlier evidence")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output.mkdir(parents=True, exist_ok=True)
    for hours in (12, 24):
        rows = eligible_events(baseline, events, hours)
        x = [e["completed_elapsed_seconds"] / 3600 for e in rows]
        y = [e["score"] for e in rows]
        best, best_y = baseline["score"], []
        for value in y:
            best = max(best, value)
            best_y.append(best)
        fig, ax = plt.subplots(figsize=(9, 4.8), layout="constrained")
        ax.axhline(baseline["score"], color="#757575", ls="--", lw=1.2, label="Fixed baseline")
        ax.step(x + [hours], best_y + [best_y[-1]], where="post", color="#135d9b",
                lw=2, label="Best available development score")
        ax.scatter(x, y, color="#e27a23", s=32, zorder=3, label="Complete development evaluations")
        skipped = [e for e in events if e["split"] == "development"
                   and e["status"] != "complete" and e["completed_elapsed_seconds"] <= hours * 3600]
        if skipped:
            ax.plot([e["completed_elapsed_seconds"] / 3600 for e in skipped],
                    [0.025] * len(skipped), "x", color="#b33d48",
                    transform=ax.get_xaxis_transform(), label="Unscored/debug event (no score)")
        ax.set(xlim=(0, hours), ylim=(0, 1), xlabel="Elapsed research wall time (hours)",
               ylabel="Development score", title=f"Coding harness evolution: first {hours} hours")
        ax.grid(alpha=.18)
        ax.legend(loc="upper left", fontsize=8)
        fig.text(.5, -.015, "Same run; evaluations and infrastructure time included. Reserved-task audit reported separately.",
                 ha="center", fontsize=8)
        for extension in ("png", "svg"):
            fig.savefig(output / f"evolution_{hours}h.{extension}", dpi=180, bbox_inches="tight")
        plt.close(fig)
    result = {"status": "rendered", "protocol_sha256": baseline["protocol_sha256"],
              "checkpoints": selections, "elapsed_seconds": elapsed,
              "metric": "development_only", "input_event_count": len(events)}
    (output / "checkpoint-selections.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(json.loads(args.run.read_text()), args.output), indent=2))


if __name__ == "__main__":
    main()
