from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from typing import Any

from io_utils import read_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a LoRA adapter with SFT or DPO."
    )
    parser.add_argument("--config", required=True, help="JSON experiment config.")
    parser.add_argument("--dataset", help="Override dataset_path in the config.")
    parser.add_argument("--output-dir", help="Override output_dir in the config.")
    parser.add_argument("--model", help="Override model_name_or_path.")
    parser.add_argument("--method", choices=("sft", "dpo"))
    return parser.parse_args()


def load_config(args: argparse.Namespace) -> dict[str, Any]:
    with open(args.config, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    overrides = {
        "dataset_path": args.dataset,
        "output_dir": args.output_dir,
        "model_name_or_path": args.model,
        "method": args.method,
    }
    config.update({key: value for key, value in overrides.items() if value})
    required = ("dataset_path", "output_dir", "model_name_or_path", "method")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise ValueError(f"Missing configuration fields: {', '.join(missing)}")
    return config


def set_seed(seed: int) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def render_sft(tokenizer: Any, sample: dict[str, str]) -> str:
    messages = [
        {"role": "user", "content": sample["prompt"]},
        {"role": "assistant", "content": sample["completion"]},
    ]
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
    return (
        f"### User:\n{sample['prompt']}\n\n"
        f"### Assistant:\n{sample['completion']}"
    )


def main() -> None:
    args = parse_args()
    config = load_config(args)
    seed = int(config.get("seed", 42))
    set_seed(seed)

    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from trl import DPOConfig, DPOTrainer, SFTConfig, SFTTrainer
    except ImportError as exc:
        raise SystemExit(
            "Install requirements-tuning.txt before starting training."
        ) from exc

    method = config["method"].lower()
    records = read_records(config["dataset_path"])
    expected = (
        ("prompt", "completion")
        if method == "sft"
        else ("prompt", "chosen", "rejected")
    )
    records = [
        item
        for item in records
        if all(isinstance(item.get(field), str) and item[field].strip() for field in expected)
    ]
    if not records:
        raise SystemExit(f"No valid {method.upper()} records found.")

    tokenizer = AutoTokenizer.from_pretrained(
        config["model_name_or_path"], trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    precision = config.get("precision", "bf16")
    dtype = torch.bfloat16 if precision == "bf16" else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        config["model_name_or_path"],
        trust_remote_code=True,
        torch_dtype=dtype,
        device_map="auto",
    )
    model.config.use_cache = False

    lora = config.get("lora", {})
    peft_config = LoraConfig(
        r=int(lora.get("r", 8)),
        lora_alpha=int(lora.get("alpha", 16)),
        lora_dropout=float(lora.get("dropout", 0.05)),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=lora.get(
            "target_modules",
            ["q_proj", "k_proj", "v_proj", "o_proj", "up_proj", "down_proj", "gate_proj"],
        ),
    )

    common = {
        "output_dir": config["output_dir"],
        "num_train_epochs": float(config.get("epochs", 3)),
        "per_device_train_batch_size": int(config.get("batch_size", 1)),
        "gradient_accumulation_steps": int(config.get("gradient_accumulation_steps", 8)),
        "learning_rate": float(config.get("learning_rate", 1e-5)),
        "warmup_ratio": float(config.get("warmup_ratio", 0.1)),
        "weight_decay": float(config.get("weight_decay", 0.01)),
        "logging_steps": int(config.get("logging_steps", 10)),
        "save_strategy": "epoch",
        "save_total_limit": int(config.get("save_total_limit", 1)),
        "gradient_checkpointing": bool(config.get("gradient_checkpointing", True)),
        "bf16": precision == "bf16",
        "fp16": precision == "fp16",
        "seed": seed,
        "report_to": config.get("report_to", "none"),
    }
    dataset = Dataset.from_list(records)

    if method == "sft":
        training_args = SFTConfig(
            **common,
            max_seq_length=int(config.get("max_length", 4096)),
        )
        trainer = SFTTrainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            tokenizer=tokenizer,
            peft_config=peft_config,
            formatting_func=lambda sample: render_sft(tokenizer, sample),
        )
    else:
        training_args = DPOConfig(
            **common,
            max_length=int(config.get("max_length", 4096)),
            max_prompt_length=int(config.get("max_prompt_length", 3072)),
            beta=float(config.get("beta", 0.1)),
        )
        trainer = DPOTrainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            tokenizer=tokenizer,
            peft_config=peft_config,
        )

    Path(config["output_dir"]).mkdir(parents=True, exist_ok=True)
    trainer.train()
    trainer.save_model(config["output_dir"])
    tokenizer.save_pretrained(config["output_dir"])
    with open(
        Path(config["output_dir"]) / "experiment_config.json",
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()

