# Recursive Coding Harness Evolution

Source and evaluation protocol for OpenRSI-Index Discussion #318.

Research question: with a frozen coding model and fixed inference budgets, do successive harness revisions improve held-out coding performance at 12 and 24 hours, including transfer to unseen programming languages and repositories?

Each iteration inherits a candidate harness, records a failure hypothesis, changes its prompts or execution policies, evaluates the complete development suite, and retains or rejects the revision. The research model is not weight-trained. The contribution is the controlled evaluation protocol and experiment, not a claim to have invented agent evolution or the reused components.

The protocol fixes 41 development tasks and 60 reserved audit tasks, two inference budgets, and the same public coding model for all candidates. A single 24-hour trajectory supplies the 12-hour prefix checkpoint and the 24-hour checkpoint. Both selections are frozen using development results before any final-audit feedback is released.

Status: source preparation and static validation only. No matched baseline, completed evolution run, or measured improvement is claimed. OpenRSI is building the executable task separately; this repository is not yet an end-to-end runnable benchmark.

## Verify the inventory and scoring contract

```sh
python3 -m pip install -r requirements-checks.txt
python3 inventory_audit.py
python3 audit.py
python3 -m unittest test_evaluation_contract.py
```

`inventory_audit.py` reads the vendored metadata without downloading or executing task code. `vendor-manifest.json` records the original Git blob identities for all copied source files. `protocol.json` defines selected tasks and budgets; `evaluation_contract.py` rejects incomplete or infrastructure-invalid evaluations and implements the fixed aggregation and checkpoint selection. Plot tests use synthetic fixtures; those fixtures are not experimental results.

The `vendor/` directory preserves existing implementation source unmodified. Its inherited launchers require adaptation to the local model broker, the specified isolation boundary, and the declared unscored infrastructure semantics. See [PROVENANCE.md](PROVENANCE.md) for authors, immutable source revisions, licenses, and the distinction between reused components and this protocol. Preserve these notices in derivatives.

The full source inventory includes reserved task identifiers and is for the operator. Do not copy it, reserved content, or verifier assets into the research agent's Work environment.

Research-paper inspiration: [Darwin Godel Machine](https://arxiv.org/abs/2505.22954), [Group-Evolving Agents](https://arxiv.org/abs/2602.04837), [Regularized Recursive Self-Improvement of Agent Harnesses](https://arxiv.org/abs/2609.24972), and [Can Coding Agents Sustain Continual Evolution without Forgetting?](https://arxiv.org/abs/2611.03219).
