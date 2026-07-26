# YuLan-OneSim Researcher: reviewer reproduction guide

This delivery contains the command-line researcher workflow, the OneSim
runtime, the paper scenario library, code-only case-study examples, and the
VR2T SFT/DPO implementation. It intentionally excludes datasets, generated
profiles, run outputs, logs, figures, model weights, and web interfaces.

## 1. Environment

Use Python 3.10 or newer. Python 3.10 is used by the supplied Dockerfile.

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
./researcher.sh --check
```

Alternatively, run `./scripts/bootstrap.sh` for the same setup and preflight.

Optional PDF compilation in the final reporting phase requires `xelatex` and
`bibtex`. Reports default to English. If the optional Chinese mode is selected,
the template uses the TeX Live bundled Fandol fonts instead of machine-specific
macOS or Windows fonts. Without the LaTeX tools, the source report remains
available.

## 2. Model configuration

The bundled configuration accepts any OpenAI-compatible chat API and contains
no credentials. The simulation defaults use list memory, so a separate
embedding API is not required.

```bash
export LLM_API_KEY="..."
export LLM_BASE_URL="https://api.example.com/v1"
export LLM_MODEL="provider-model-id"
export LLM_PROVIDER="openai"  # optional; this is the default
./researcher.sh --check-api
```

When using OpenAI directly, `LLM_BASE_URL` can be omitted. The entry script also
maps the conventional `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`
variables. For backward compatibility, the earlier `DEEPSEEK_API_KEY`,
`DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL` variables are accepted and select the
DeepSeek-specific adapter automatically.

`--check` is offline and validates the installation. `--check-api` additionally
makes one short, billable model request to verify the endpoint, credential, and
model name.

The OpenAI-compatible request path can be tested without external credentials
or billing by running:

```bash
make check-api-mock
```

For a non-OpenAI-compatible service or a multi-model setup, pass a replacement
JSON file with `--model-config` and select its `config_name` with
`--model-name`. The bundled model's config name is `default-chat`; `LLM_MODEL`
is the provider's actual API model identifier.

`SEMANTIC_SCHOLAR_API_KEY` is optional and only affects literature-search rate
limits in the report phase.

## 3. Complete command-line workflow

Run from the repository root:

```bash
./researcher.sh \
  --project-name reviewer_demo \
  --scenario "A small community public-goods game in which agents decide whether to contribute under different visibility conditions." \
  --question "How does contribution visibility affect cooperation?" \
  --paradigm inductive \
  --phase full
```

The five phases are:

1. environment design;
2. executable scenario generation;
3. simulation experiment execution;
4. statistical and figure analysis;
5. LaTeX report generation.

Generated inputs, code, results, and reports are written under
`projects/reviewer_demo/`. Generated simulation environments are written under
`src/envs/`. Project outputs and generated scenario data are ignored by Git;
newly generated environment source directories should be reviewed before they
are added to a submission.

For phase-by-phase debugging, rerun the same project with `--phase design`,
`--phase scenario`, `--phase execute`, `--phase analysis`, or `--phase report`.
Workflow state is persisted in the project directory.
Scenario-generation artifacts are checkpointed independently; rerunning the
scenario phase resumes at the first missing artifact.

Generated scenario code is checked locally for required files, valid JSON, and
valid Python syntax. The legacy LLM-assisted Docker repair loop is optional and
can be enabled with `ONESIM_ENABLE_DOCKER_DEBUG=1` when its Docker environment
has been configured.

The bundled simulation configuration enables the monitor component so generated
scene metrics are written for the analysis phase.

## 4. Validation record

On 2026-07-26, the generic API path was tested against a real
OpenAI-compatible DeepSeek endpoint with model `deepseek-v4-flash`. A minimal one-group,
one-replicate project completed all five phases; the simulation result was 1/1
successful, analysis figures and LaTeX sources were generated, and the report
compiled successfully with XeLaTeX. Credentials and generated outputs are not
included in this delivery.

## 5. Docker alternative

```bash
docker build -t onesim-researcher .
docker run --rm \
  -e LLM_API_KEY \
  -e LLM_BASE_URL \
  -e LLM_MODEL \
  -v "$PWD/projects:/app/projects" \
  onesim-researcher \
  --project-name reviewer_demo \
  --scenario "A small public-goods game." \
  --question "What affects cooperation?" \
  --paradigm inductive \
  --phase full
```

The workflow makes external LLM calls. Runtime, token usage, and cost depend on
the generated scenario and chosen model.

## 6. Paper artifacts

The canonical list of the 50 evaluated scenarios is
`src/envs/paper_scenarios.json`. The two available repository snapshots contain
complete executable code for 49 of them. `cultural_globalization` is absent
from both snapshots and the archive. The manifest records this source gap; it
must be restored before claiming full 50-scenario execution.

Code-only launchers for the three paper case studies are documented in
`examples/paper_cases/README.md`. They generate deterministic synthetic
profiles and relationship networks at runtime for smoke testing. Restricted
CEPS inputs and human-participant records are not included.

VR2T data preparation, OpenAI-compatible response refinement, SFT, and DPO are
documented in `src/llm_tuning/README.md`. Training dependencies are isolated
in `requirements-tuning.txt`.

Run the complete offline submission audit with:

```bash
make check-all
```
