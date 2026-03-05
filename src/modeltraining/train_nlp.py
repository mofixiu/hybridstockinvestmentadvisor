import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from datasets import Dataset
import os

def fine_tune_finbert():
    print("🧠 Starting Naija-FinBERT Fine-Tuning...")

    # 1. Load the Custom Nigerian Dataset
    data_path = "data/raw/sentimentData/naija_sentiment.csv"
    if not os.path.exists(data_path):
        print("❌ Dataset not found! Create data/raw/sentimentData/naija_sentiment.csv first.")
        return

    df = pd.read_csv(data_path)
    # Convert pandas dataframe to HuggingFace Dataset format
    dataset = Dataset.from_pandas(df)

    # 2. Load the Pre-trained FinBERT Model & Tokenizer
    model_name = "ProsusAI/finbert"
    print(f"📥 Loading base model: {model_name}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # FinBERT has 3 labels: 0=Positive, 1=Negative, 2=Neutral (Wait, Finbert default is actually: 0=Positive, 1=Negative, 2=Neutral. Let's remap to match standard 0=Neg, 1=Neu, 2=Pos to avoid confusion)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=3, ignore_mismatched_sizes=True)

    # 3. Tokenize the Data (Translate text into numbers for the AI)
    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=64)

    print("✂️ Tokenizing the Naija slang...")
    tokenized_datasets = dataset.map(tokenize_function, batched=True)

    # 4. Split into Train and Test (80/20)
    tokenized_datasets = tokenized_datasets.train_test_split(test_size=0.2, seed=42)

    # 5. Define Training Arguments (How the AI should learn)
    training_args = TrainingArguments(
        output_dir="./models/naija_finbert_results",
        eval_strategy="epoch",  # Check performance every epoch
        learning_rate=2e-5,
        per_device_train_batch_size=4, # Small batch size for laptops
        num_train_epochs=3,            # Study the data 3 times
        weight_decay=0.01,
        save_strategy="epoch",
        logging_dir='./logs',
    )

    # 6. Initialize the Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
    )

    # 7. Train the Model!
    print("🚀 Training started! (This might take a few minutes depending on your Mac's CPU/M-chip)")
    trainer.train()

    # 8. Save the localized model
    save_path = "models/naija_finbert"
    model.save_pretrained(save_path)
    tokenizer.save_pretrained(save_path)
    
    print(f"✅ Success! Localized Naija-FinBERT saved to {save_path}")

if __name__ == "__main__":
    fine_tune_finbert()