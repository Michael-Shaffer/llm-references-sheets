import os
import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
try:
    from trl import SFTTrainer, SFTConfig
except ImportError:
    from trl import SFTTrainer
    SFTConfig = None

# Configuration
MODEL_NAME = "/opt/models/Meta-Llama-3.1-8B-Instruct"
# Get absolute path to the data directory relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATASET_PATH = os.path.join(PROJECT_ROOT, "data", "dataset.jsonl")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "models", "stars-adapter")

def main():
    print(f"Loading model: {MODEL_NAME}")
    
    # 1. Load Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # 2. Load Quantization Config (4-bit)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=False,
    )

    # 3. Load Base Model
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    
    # Prepare model for k-bit training
    model = prepare_model_for_kbit_training(model)

    # 4. LoRA Configuration
    peft_config = LoraConfig(
        lora_alpha=16,
        lora_dropout=0.1,
        r=64,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # 5. Load Dataset
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
    
    # formatting function for instruction dataset
    def formatting_prompts_func(examples):
        output_texts = []
        
        # Handle both batched (dict of lists) and single (dict) inputs
        instructions = examples['instruction']
        inputs = examples.get('input', []) # might be missing or None
        outputs = examples['output']
        
        # If 'instructions' is a string, it's a single example (batched=False)
        if isinstance(instructions, str):
            # For single example (batched=False), we must return a single string, NOT a list
            input_text = inputs if inputs else ""
            if input_text:
                return f"### Instruction:\n{instructions}\n\n### Input:\n{input_text}\n\n### Response:\n{outputs}"
            else:
                return f"### Instruction:\n{instructions}\n\n### Response:\n{outputs}"
        
        # Batched logic (returns list)
        for i in range(len(instructions)):
            instruction = instructions[i]
            input_text = inputs[i] if i < len(inputs) and inputs[i] else ""
            output = outputs[i]
            
            if input_text:
                text = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
            else:
                text = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
            output_texts.append(text)
            
        return output_texts

    # 6. Training Arguments / SFT Config
    if SFTConfig:
        # Newer trl versions use SFTConfig, but max_seq_length might still be required in Trainer for some versions
        training_args = SFTConfig(
            output_dir=OUTPUT_DIR,
            num_train_epochs=3,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            optim="paged_adamw_32bit",
            save_steps=25,
            logging_steps=10,
            learning_rate=2e-4,
            weight_decay=0.001,
            fp16=True,
            bf16=False,
            max_grad_norm=0.3,
            max_steps=-1,
            warmup_ratio=0.03,
            group_by_length=True,
            lr_scheduler_type="constant",
            report_to="none", # Changed from tensorboard to none to avoid error
            # max_seq_length=2048, # Removed to avoid errors
            # packing=False,       # Removed to avoid errors
        )
        
        # 7. Trainer
        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset,
            peft_config=peft_config,
            processing_class=tokenizer,
            args=training_args,
            formatting_func=formatting_prompts_func,
        )
    else:
        # Older trl versions
        training_args = TrainingArguments(
            output_dir=OUTPUT_DIR,
            num_train_epochs=3,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            optim="paged_adamw_32bit",
            save_steps=25,
            logging_steps=10,
            learning_rate=2e-4,
            weight_decay=0.001,
            fp16=True,
            bf16=False,
            max_grad_norm=0.3,
            max_steps=-1,
            warmup_ratio=0.03,
            group_by_length=True,
            lr_scheduler_type="constant",
            report_to="none" # Changed from tensorboard to none
        )

        # 7. Trainer
        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset,
            peft_config=peft_config,
            max_seq_length=2048,
            tokenizer=tokenizer,
            args=training_args,
            formatting_func=formatting_prompts_func,
            packing=False,
        )

    print("Starting training...")
    trainer.train()
    
    print(f"Saving model to {OUTPUT_DIR}")
    trainer.model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

if __name__ == "__main__":
    main()

