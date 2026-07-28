# S-Researcher

S-Researcher is the command-line research workflow accompanying
**“LLM Agents as Social Scientists: A Human–AI Collaborative Platform for
Social Science Automation”**.
It uses YuLan-OneSim to turn a social-science question into an experimental
design, executable agent simulation, quantitative analysis, and English
research report.

This repository is a code-focused supplement. It includes the Researcher
workflow, simulation runtime, paper scenario source, VR2T tuning utilities,
and small synthetic initialization files used by the bundled environments.
It excludes empirical datasets, generated agent profiles, human-participant
records, run outputs, model weights, and API credentials.

## What is included

| Component | Location | Purpose |
| --- | --- | --- |
| Research workflow | `src/researcher.py`, `src/researcher/` | Design, scenario generation, execution, analysis, and reporting |
| Simulation runtime | `src/onesim/`, `src/main.py` | Event-driven agent simulation |
| Paper scenarios | `src/envs/` | Curated scenario source and configuration |
| VR2T tuning | `src/llm_tuning/` | Data preparation, refinement, SFT, and DPO |

## Requirements

- Python 3.10 or newer
- An OpenAI-compatible chat API for model-backed workflow phases
- Optional: XeLaTeX and BibTeX for compiling the final PDF report
- Optional: CUDA-capable hardware for VR2T fine-tuning

The research code was tested on an Ubuntu Linux server with Python 3.10 and
eight NVIDIA A100 GPUs. The API-backed Researcher workflow and reviewer demo
do not require local GPU hardware; the A100 GPUs are relevant only to local
VR2T training. All Python dependency constraints and minimum versions are
listed in `requirements.txt`, while the separate tuning dependencies are in
`requirements-tuning.txt`.

## Installation

The following command creates `.venv` and installs the Researcher dependencies
and package:

```bash
./scripts/setup.sh
```

The command-line entry point automatically uses `.venv` when it is present, so
activation is optional. The equivalent manual installation is:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
```

Typical installation takes approximately 5–10 minutes on a broadband-connected
desktop computer. Download time for the scientific Python dependencies is the
main source of variation.

## Model configuration

The bundled model configuration contains environment-variable placeholders,
not credentials. Configure any OpenAI-compatible endpoint:

```bash
export LLM_API_KEY="your-api-key"
export LLM_MODEL="provider-model-id"
export LLM_BASE_URL="https://api.example.com/v1"
export LLM_PROVIDER="openai"
```

`LLM_BASE_URL` may be omitted for the official OpenAI API.
`OPENAI_API_KEY`/`OPENAI_BASE_URL`/`OPENAI_MODEL` and the corresponding
`DEEPSEEK_*` variables are accepted as compatibility aliases.

Never commit a populated model configuration or an API key.

## Reviewer demo on synthetic data

The bundled `collective_action_problem` environment is the small simulated
dataset used for the reviewer demo. Its initial state is stored in
`src/envs/collective_action_problem/env_data.json`; its agent schemas, actions,
and events are stored in the same environment directory. The bounded
`config/demo_config.json` configuration runs one simulation round with one
Individual agent and one Group agent.

After configuring an OpenAI-compatible API as described above, run:

```bash
.venv/bin/python src/main.py \
  --config config/demo_config.json \
  --model_config config/model_config.json \
  --model_config_name default-chat \
  --env collective_action_problem \
  --output_dir projects/reviewer_env_demo/output \
  --log_dir projects/reviewer_env_demo/logs
```

On the first run, the software generates two synthetic agent profiles through
the configured API. These generated profiles are written under
`src/envs/collective_action_problem/profile/data/` and are ignored by Git.
They are generated inputs, not empirical or human-participant data.

A successful run exits with status 0, logs `All steps (rounds) completed`, and
creates the following output structure:

```text
projects/reviewer_env_demo/
├── logs/
│   └── collective_action_problem.log
└── output/
    └── metrics_plots/
        └── step_1/
            ├── general/
            │   ├── general_metrics.json
            │   ├── round_duration.png
            │   └── total_tokens.png
            └── profiles/
                └── profiles_<timestamp>.json
```

A clean real-API run, including first-time profile generation, completed in
51.6 seconds during the submission test on 28 July 2026. Allow approximately
1–3 minutes on a normal desktop because runtime depends on the selected API,
model response speed, network latency, and first-time Matplotlib font-cache
generation. LLM-generated profile values and numerical outcomes may vary, but
the output structure and successful termination condition are fixed.

To run a different bundled environment, use `config/config.json` and replace
the `--env` value with a directory name from `src/envs/`.

## Run the complete Researcher workflow

```bash
./researcher.sh \
  --project-name reviewer_demo \
  --scenario "A small community public-goods game with different contribution-visibility conditions." \
  --question "How does contribution visibility affect cooperation?" \
  --paradigm inductive \
  --phase full
```

The full workflow runs five phases:

1. environment and experimental design;
2. executable scenario generation;
3. simulation execution;
4. statistical and figure analysis;
5. English LaTeX report generation.

Artifacts are written to `projects/<project-name>/`, which is ignored by Git.
The workflow saves checkpoints in `workflow_state.json`; rerun an individual
phase with `--phase design`, `scenario`, `execute`, `analysis`, or `report`.

An equivalent JSON-driven example is available at
`config/research_config.example.json`:

```bash
./researcher.sh \
  --config config/research_config.example.json \
  --project-name demo
```

For a new research input, copy the example JSON and replace
`scenario_description`, `research_question`, and `research_paradigm`, or pass
the corresponding `--scenario`, `--question`, and `--paradigm` options. No
external empirical dataset is required by the standard Researcher workflow.

Use `./researcher.sh --help` for all options.

## Docker

Build the command-line image and verify its entry point:

```bash
docker build -t s-researcher .
docker run --rm s-researcher --help
```

Mount `/app/projects` when generated outputs should persist on the host.

## VR2T tuning

Install the isolated tuning dependencies:

```bash
.venv/bin/python -m pip install -r requirements-tuning.txt
```

The tuning package supports rated-decision normalization, optional
OpenAI-compatible response refinement, LoRA SFT, LoRA DPO, and repeated VR2T
rounds. No training examples, adapters, checkpoints, or model weights are
included. See [`src/llm_tuning/README.md`](src/llm_tuning/README.md).

## Reproducibility

Detailed phase commands, output locations, and model configuration are in
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
