# YuLan-OneSim Researcher: reviewer reproduction guide

This delivery contains the command-line researcher workflow, the OneSim
runtime, the paper scenario library, and the VR2T SFT/DPO implementation. It
intentionally excludes datasets, generated profiles, run outputs, logs,
figures, model weights, and web interfaces.

## 1. Environment

Use Python 3.10 or newer. Python 3.10 is used by the supplied Dockerfile.

Run the setup script to create `.venv` and install the package and
dependencies. The entry script automatically uses the local virtual
environment:

```bash
./scripts/setup.sh
```

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
```

When using OpenAI directly, `LLM_BASE_URL` can be omitted. The entry script also
maps the conventional `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`
variables.

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

Generated scenarios require the expected source files, valid JSON, and valid
Python syntax. The legacy LLM-assisted Docker repair loop is optional and can
be enabled with `ONESIM_ENABLE_DOCKER_DEBUG=1` when its Docker environment has
been configured.

The bundled simulation configuration enables the monitor component so generated
scene metrics are written for the analysis phase.


## 4. VR2T tuning

VR2T data preparation, OpenAI-compatible response refinement, SFT, and DPO are
documented in `src/llm_tuning/README.md`. Training dependencies are isolated
in `requirements-tuning.txt`.
