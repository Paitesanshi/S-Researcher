# Paper scenario library

This directory contains the code and configuration for the 50 scenarios
reported in the paper. `paper_scenarios.json` is the canonical manifest.

Only source artifacts are included:

- workflow and environment JSON configuration;
- agent, event, environment, and metric source code;
- profile schemas and profile-generation source code.

Generated profiles, simulation events, logs, plots, run directories, and other
experiment outputs are intentionally excluded.

Run a scenario from the repository root:

```bash
python examples/paper_cases/run_case.py \
  --case cultural_dissemination \
  --replicate 1 \
  --smoke \
  --model-config config/model_config.json
```

The two available repository snapshots contain complete executable source for
49 of the 50 evaluated scenarios. `cultural_globalization` is absent from both
snapshots and the archive. It remains listed in the manifest so the submitted
list stays aligned with the paper. Its original code must be restored before
claiming that all 50 scenarios are executable.
