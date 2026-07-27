# S-Researcher

S-Researcher is the command-line research workflow accompanying
**“LLM Agents as Social Scientists: A Human–AI Collaborative Platform for
Social Science Automation”**.
It uses YuLan-OneSim to turn a social-science question into an experimental
design, executable agent simulation, quantitative analysis, and English
research report.

This repository is a code-only supplement. It includes the Researcher
workflow, simulation runtime, paper scenario source, and VR2T tuning
utilities. It excludes datasets, generated agent profiles, human-participant
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
