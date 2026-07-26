# Paper case-study code

This directory contains code-only reproductions of the three case-study
simulation designs:

- `cultural_dissemination`: inductive Axelrod-style cultural dissemination;
- `teacher_attention`: deductive teacher-attention allocation;
- `public_goods`: abductive public-goods leadership experiment.

The executable environment implementations are stored in `src/envs`. No
original profiles, CEPS records, human-participant data, run output, or figures
are included.

## Smoke run

From the repository root:

```bash
python examples/paper_cases/run_case.py \
  --case cultural_dissemination \
  --replicate 1 \
  --smoke \
  --model-config config/model_config.json
```

This command executes the simulation and therefore requires a configured model
API. To validate profile and configuration generation without making an API
request, add `--prepare-only`, or run all three preparation checks with:

```bash
make smoke-cases
```

Replace `--case` with `teacher_attention` or `public_goods`. For the latter
two, select a condition:

```bash
python examples/paper_cases/run_case.py \
  --case teacher_attention \
  --condition expression \
  --replicate 1 \
  --smoke \
  --model-config config/model_config.json

python examples/paper_cases/run_case.py \
  --case public_goods \
  --condition voluntary-high \
  --replicate 1 \
  --smoke \
  --model-config config/model_config.json
```

Teacher-attention conditions are `expression`, `merit`, and `socioeconomic`.
Public-goods conditions are the Cartesian product of decision mechanism
(`voluntary`, `forced`) and leader contribution (`low`, `medium`, `high`), for
example `forced-medium`.

Omit `--smoke` to use the paper-scale agent counts. Synthetic profiles are
created at runtime under `artifacts/paper_cases`; they are not part of the
submission. To reproduce the empirical teacher-attention study, replace the
synthetic profiles with profiles produced by
`src/envs/teacher_attention_allocation/profile/build_ceps_profiles.py` from an
authorized CEPS copy.
