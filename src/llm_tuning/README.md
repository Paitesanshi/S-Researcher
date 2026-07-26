# VR2T tuning code

This package contains the code-only SFT and DPO workflow used for the VR2T
experiments. It is independent of the OneSim web backend and accepts local
Hugging Face model paths or model identifiers.

## Installation

```bash
pip install -r requirements-tuning.txt
```

## Input format

Input may be a JSON array or JSON Lines file. The required rated-decision
fields are defined in `schemas/rated_decision.schema.json`.

- SFT uses `feedback` as the preferred completion and falls back to `output`.
- DPO uses `chosen`/`rejected`, `feedback`/`output`, or the highest- and
  lowest-rated outputs sharing a prompt.

No training data are included in this repository.

## Prepare and train

```bash
python src/llm_tuning/prepare_data.py \
  --input /path/to/rated_decisions.jsonl \
  --output artifacts/vr2t/round_1/sft.jsonl \
  --method sft \
  --seed 42

python src/llm_tuning/train.py \
  --config src/llm_tuning/configs/qwen2.5-1.5b-sft.json
```

Use the matching DPO configuration for preference optimization. Configurations
for the Qwen2.5-1.5B-Instruct and Llama-3.2-1B-Instruct experiments are
provided.

## One VR2T round

```bash
python src/llm_tuning/run_vr2t.py \
  --ratings /path/to/round_1_ratings.jsonl \
  --work-dir artifacts/vr2t \
  --round 1 \
  --method dpo \
  --config src/llm_tuning/configs/qwen2.5-1.5b-dpo.json \
  --refine
```

`--refine` is optional and works with any OpenAI-compatible endpoint:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.example.com"
export OPENAI_MODEL="model-name"
```

Repeat the command for rounds 1 through 4 using the rated decisions produced
by the corresponding simulation/evaluation round. API credentials, model
weights, adapters, MLflow/W&B outputs, and training datasets are not committed.
