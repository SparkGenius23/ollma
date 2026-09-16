import torch
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments

max_seq_length = 2048
load_in_4bit = True  # Enable 4-bit QLoRA to save GPU VRAM

# 1. Load Base Model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "openai/gpt-oss-20b",
    max_seq_length = max_seq_length,
    load_in_4bit = load_in_4bit,
)

# 2. Attach LoRA Adapters
model = FastLanguageModel.get_peft_model(
    model,
    r = 16,               # LoRA Rank (higher = more memory/capacity)
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
)

# 3. Format dataset inputs
def format_prompts(examples):
    texts = []
    for inst, out in zip(examples["instruction"], examples["output"]):
        text = f"<|user|>\n{inst}\n<|assistant|>\n{out}"
        texts.append(text)
    return { "text" : texts }

dataset = load_dataset("json", data_files="dataset.jsonl", split="train")
dataset = dataset.map(format_prompts, batched = True)

# 4. Set up Trainer
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    packing = False,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 100,             # Adjust steps based on your dataset size
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 1,
        output_dir = "outputs",
    ),
)

# 5. Execute Training
trainer.train()

# 6. Export directly as a quantized GGUF file for Ollama
model.save_pretrained_gguf(
    "rhythmx_finetuned_gguf", 
    tokenizer, 
    quantization_method = "q4_k_m"
)