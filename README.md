# S-Researcher

S-Researcher is the command-line research workflow accompanying
**“LLM Agents as Social Scientists: A Human–AI Collaborative Platform for
Social Science Automation”** ([arXiv:2604.01520](https://arxiv.org/abs/2604.01520)).
It uses YuLan-OneSim to turn a social-science question into an experimental
design, executable agent simulation, quantitative analysis, and English
research report.

This repository is a code-only supplement. It includes the Researcher
workflow, simulation runtime, paper scenario source, three case-study
launchers, and VR2T tuning utilities. It excludes datasets, generated agent
profiles, human-participant records, run outputs, model weights, and API
credentials.

## What is included

| Component | Location | Purpose |
| --- | --- | --- |
| Research workflow | `src/researcher.py`, `src/researcher/` | Design, scenario generation, execution, analysis, and reporting |
| Simulation runtime | `src/onesim/`, `src/main.py` | Event-driven agent simulation |
| Paper scenarios | `src/envs/` | Curated scenario source and configuration |
| Scenario manifest | `src/envs/paper_scenarios.json` | Canonical list of the 50 evaluated scenarios |
| Paper case studies | `examples/paper_cases/` | Inductive, deductive, and abductive examples |
| VR2T tuning | `src/llm_tuning/` | Data preparation, refinement, SFT, and DPO |
| Submission validation | `scripts/validate_submission.py` | Syntax, JSON, manifest, and code-only checks |

## Requirements

- Python 3.10 or newer
- An OpenAI-compatible chat API for model-backed workflow phases
- Optional: XeLaTeX and BibTeX for compiling the final PDF report
- Optional: CUDA-capable hardware for VR2T fine-tuning

## Installation

The bootstrap script creates `.venv`, installs the Researcher dependencies,
installs the package in editable mode, and runs the offline preflight:

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
```

The equivalent manual installation is:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
./researcher.sh --check
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

Verify local imports without making a network request:

```bash
./researcher.sh --check
```

Verify the endpoint with one short, billable model request:

```bash
./researcher.sh --check-api
```

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
  --project-name reviewer_demo
```

Use `./researcher.sh --help` for all options.

## Paper case studies

The case-study launcher creates deterministic synthetic profiles at runtime,
so its preparation path can be tested without private data or an API:

```bash
make smoke-cases
```

The three included designs are:

- inductive cultural dissemination;
- deductive teacher-attention allocation;
- abductive public-goods leadership.

See [`examples/paper_cases/README.md`](examples/paper_cases/README.md) for
conditions, paper-scale runs, and the CEPS profile-builder interface.

## VR2T tuning

Install the isolated tuning dependencies:

```bash
make install-tuning
```

The tuning package supports rated-decision normalization, optional
OpenAI-compatible response refinement, LoRA SFT, LoRA DPO, and repeated VR2T
rounds. No training examples, adapters, checkpoints, or model weights are
included. See [`src/llm_tuning/README.md`](src/llm_tuning/README.md).

## Validate the supplement

Run all offline checks:

```bash
make check-all
```

The checks cover the installed Researcher imports, a local mock
OpenAI-compatible API request, Python syntax, JSON configuration, the 50-name
scenario manifest, forbidden data artifacts, shell entry points, and
preparation of all three paper cases.

The source snapshots available for this release contain complete executable
source for 49 of the 50 manifest scenarios. `cultural_globalization` is absent
from the original repository, the `v1.0` snapshot, and the supplied archive.
The manifest records this provenance gap rather than substituting a different
scenario. Run `python scripts/validate_submission.py --strict-scenarios` if a
future release should require all 50 scenario directories.

## Reproducibility and citation

Detailed phase commands, output locations, Docker usage, model configuration,
and the recorded real-API validation are in
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

Citation metadata are provided in [`CITATION.cff`](CITATION.cff).

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
