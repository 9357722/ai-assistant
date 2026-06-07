import os
import torch
import json
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

# 脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ========== 1. 加载训练数据 ==========
with open(os.path.join(SCRIPT_DIR, "training_data.json"), "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# 转换成对话格式
formatted_data = []
for item in raw_data:
    text = f"### 指令:\n{item['instruction']}\n\n### 回复:\n{item['output']}"
    formatted_data.append({"text": text})

dataset = Dataset.from_list(formatted_data)

# ========== 2. 加载模型和分词器 ==========
# 使用一个小模型做实验（免费，几百MB）
model_name = "Qwen/Qwen2.5-0.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float32,
    trust_remote_code=True
)

# ========== 3. 配置 LoRA ==========
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8,               # LoRA 秩，越小越省资源
    lora_alpha=32,
    lora_dropout=0.1,
    target_modules=["q_proj", "v_proj"]  # 只训练注意力层的 Q 和 V
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()  # 看训练参数量

# ========== 4. 数据预处理 ==========
def tokenize_function(examples):
    tokens = tokenizer(
        examples["text"],
        truncation=True,
        padding="max_length",
        max_length=256
    )
    tokens["labels"] = tokens["input_ids"].copy()
    return tokens

tokenized_dataset = dataset.map(tokenize_function, batched=True)

# ========== 5. 训练参数 ==========
training_args = TrainingArguments(
    output_dir=os.path.join(SCRIPT_DIR, "lora_output"),
    num_train_epochs=3,          # 只训练 3 轮
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    logging_steps=1,
    save_steps=100,
    learning_rate=2e-4,
    fp16=torch.cuda.is_available(),
    report_to="none"
)

# ========== 6. 开始训练 ==========
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)
)

print("开始 LoRA 微调训练...")
trainer.train()

# ========== 7. 保存模型 ==========
lora_path = os.path.join(SCRIPT_DIR, "lora_model")
model.save_pretrained(lora_path)
tokenizer.save_pretrained(lora_path)
print(f"训练完成！模型已保存到 {lora_path}")
