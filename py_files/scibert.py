"""
SciBERT SDL Classifier - Training and Inference

Trains a SciBERT model to classify Self-Driving Laboratory papers and scores the full dataset.
"""
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import os, re, time
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    Trainer, 
    TrainingArguments,
    DataCollatorWithPadding
)
from datasets import Dataset

# ==============================================================================
# CONFIGURATION
# ==============================================================================
PROJECT_DIR = "/project/def-kmcel/hridansh/openalex_project"
INPUT_FILE = f"{PROJECT_DIR}/data/regression/regression_dataset_subset.csv"

OUTPUT_DIR = f"{PROJECT_DIR}/data/scibert/test_2"
RESULTS_FILE = f"{OUTPUT_DIR}/scores.csv"

MODEL_NAME = f"{PROJECT_DIR}/data/scibert_model"

# Training parameters
max_length = 512
batch_size = 16        
epochs = 4          
learning_rate = 2e-5  
train_split = 0.85

# Optional improvements
use_focal_loss = False      
label_smoothing = 0.0       
grad_accum_steps = 1        

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================================================================
# FOCAL LOSS
# ==============================================================================

class FocalLoss(nn.Module):
    """Focal loss for hard examples"""
    def __init__(self, alpha=0.25, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
    
    def forward(self, inputs, targets):
        ce_loss = nn.functional.cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = self.alpha * (1-pt)**self.gamma * ce_loss
        return focal_loss.mean()

# ==============================================================================
# TEXT PROCESSING
# ==============================================================================

def clean_text(text):
    """Remove metadata artifacts"""
    if pd.isna(text):
        return ""
    
    text = str(text)
    
    patterns = [
        r'©\s*\d{4}', r'copyright\s+\d{4}',
        r'elsevier|wiley|springer|nature publishing|american chemical society|royal society of chemistry',
        r'http[s]?://\S+', r'www\.\S+', r'doi:\s*\S+', r'\S+@\S+',
        r'altmetric\s*\d+',
        r'all rights reserved|supplementary material|supporting information'
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return re.sub(r'\s+', ' ', text).strip()

# ==============================================================================
# DATA PREPARATION
# ==============================================================================

def load_data():
    """Load dataset and create labels"""
    print(f"Loading data from {INPUT_FILE}")
    start_time = time.time()
    
    df = pd.read_csv(INPUT_FILE, low_memory=False).reset_index(drop=True)
    print(f"  Loaded {len(df):,} papers in {time.time() - start_time:.2f}s")
    
    # Clean text
    df['title'] = df['title'].fillna("").apply(clean_text)
    df['abstract'] = df['abstract'].fillna("").apply(clean_text)
    df['text'] = df['title'] + " [SEP] " + df['abstract']
    
    # Create labels
    df['SDL_Brown'] = df['SDL_Brown'].fillna(0).astype(int)
    df['SDL_Tomet'] = df['SDL_Tomet'].fillna(0).astype(int)
    df['label'] = ((df['SDL_Brown'] == 1) | (df['SDL_Tomet'] == 1)).astype(int)
    
    count_positive = df['label'].sum()
    count_negative = (df['label'] == 0).sum()
    
    print(f"  SDL papers: {count_positive:,}")
    print(f"  Background: {count_negative:,}")
    
    return df

def create_balanced_dataset(df):
    """Create 1:1 balanced training set"""
    positives = df[df['label'] == 1].copy()
    negatives = df[df['label'] == 0].sample(n=len(positives), random_state=42)
    
    balanced = pd.concat([positives, negatives], ignore_index=True)
    return balanced.sample(frac=1, random_state=42).reset_index(drop=True)

def tokenize_batch(examples, tokenizer):
    """Tokenize text for BERT"""
    return tokenizer(
        examples["text"],
        truncation=True,
        padding="max_length",
        max_length=max_length
    )

# ==============================================================================
# EVALUATION
# ==============================================================================

def compute_metrics(eval_pred):
    """Compute metrics during training"""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    
    tn, fp, fn, tp = confusion_matrix(labels, predictions).ravel()
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {'precision': precision, 'recall': recall, 'f1': f1}

# ==============================================================================
# CUSTOM TRAINER
# ==============================================================================

class CustomTrainer(Trainer):
    """Custom trainer with focal loss and label smoothing options"""
    
    def __init__(self, *args, use_focal_loss=False, label_smoothing=0.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_focal_loss = use_focal_loss
        self.label_smoothing = label_smoothing
        if use_focal_loss:
            self.focal_loss = FocalLoss()
    
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        """Compute loss with optional modifications"""
        labels = inputs.get("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        
        if labels is None:
            labels = inputs.pop("labels")
        
        if self.use_focal_loss:
            loss = self.focal_loss(logits, labels)
        elif self.label_smoothing > 0:
            loss_fct = nn.CrossEntropyLoss(label_smoothing=self.label_smoothing)
            loss = loss_fct(logits, labels)
        else:
            loss = outputs.loss
        
        if loss is None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits, labels)
        
        return (loss, outputs) if return_outputs else loss

# ==============================================================================
# MAIN PIPELINE
# ==============================================================================

def main():
    """Main training and inference pipeline"""
    
    print("\n" + "="*70)
    print("SciBERT SDL Classifier")
    print("="*70)
    print(f"LR: {learning_rate}, Batch: {batch_size}, Epochs: {epochs}")
    print(f"Focal Loss: {use_focal_loss}, Label Smoothing: {label_smoothing}")
    
    start_time = time.time()
    
    # Load data
    print("\n--- STEP 1: DATA LOADING ---")
    full_df = load_data()
    balanced_df = create_balanced_dataset(full_df)
    
    # Split
    print("\n--- STEP 2: TRAIN/VAL SPLIT ---")
    train_df, val_df = train_test_split(
        balanced_df,
        train_size=train_split,
        random_state=42,
        stratify=balanced_df['label']
    )
    print(f"  Training: {len(train_df):,} | Validation: {len(val_df):,}")
    
    # Load model
    print("\n--- STEP 3: LOADING MODEL ---")
    print(f"  Model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
    
    # Tokenize
    print("\n--- STEP 4: TOKENIZING ---")
    train_dataset = Dataset.from_pandas(train_df[['text', 'label']])
    val_dataset = Dataset.from_pandas(val_df[['text', 'label']])
    
    train_dataset = train_dataset.map(
        lambda x: tokenize_batch(x, tokenizer), batched=True
    )
    val_dataset = val_dataset.map(
        lambda x: tokenize_batch(x, tokenizer), batched=True
    )
    print(f"  Train: {len(train_dataset):,} | Val: {len(val_dataset):,}")
    
    # Training setup
    print("\n--- STEP 5: TRAINING SETUP ---")
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=learning_rate,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        num_train_epochs=epochs,
        gradient_accumulation_steps=grad_accum_steps,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        save_total_limit=1,
        logging_steps=50,
        fp16=True,
        report_to="none",
        seed=42
    )
    
    trainer = CustomTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
        use_focal_loss=use_focal_loss,
        label_smoothing=label_smoothing
    )
    
    # Train
    print("\n--- STEP 6: TRAINING ---")
    training_start = time.time()
    trainer.train()
    training_duration = time.time() - training_start
    print(f"  COMPLETED: Training in {training_duration:.2f}s")
    
    # Validation
    print("\n--- STEP 7: VALIDATION ---")
    val_results = trainer.evaluate()
    print(f"  Precision: {val_results['eval_precision']:.4f}")
    print(f"  Recall:    {val_results['eval_recall']:.4f}")
    print(f"  F1:        {val_results['eval_f1']:.4f}")
    
    # Save model
    print("\n--- STEP 8: SAVING MODEL ---")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"  Saved to: {OUTPUT_DIR}")
    
    # Inference
    print("\n--- STEP 9: INFERENCE ---")
    inference_start = time.time()
    
    full_dataset = Dataset.from_pandas(full_df[['text']])
    full_dataset = full_dataset.map(
        lambda x: tokenize_batch(x, tokenizer), batched=True
    )
    
    print(f"  Scoring {len(full_dataset):,} papers...")
    full_predictions = trainer.predict(full_dataset)
    full_probs = torch.nn.functional.softmax(
        torch.tensor(full_predictions.predictions), dim=-1
    )[:, 1].numpy()
    
    inference_duration = time.time() - inference_start
    print(f"  COMPLETED: Inference in {inference_duration:.2f}s")
    
    # Save results
    print("\n--- STEP 10: SAVING RESULTS ---")
    results_df = full_df[[
        'article_id', 'doi', 'title', 'publication_year', 'field',
        'SDL_Brown', 'SDL_Tomet'
    ]].copy()
    
    results_df['scibert_prob'] = full_probs
    results_df.to_csv(RESULTS_FILE, index=False)
    print(f"  Results: {RESULTS_FILE}")
    
    # Summary
    print("\n--- STEP 11: SUMMARY ---")
    known_sdl = results_df[(results_df['SDL_Brown'] == 1) | (results_df['SDL_Tomet'] == 1)]
    background = results_df[(results_df['SDL_Brown'] == 0) & (results_df['SDL_Tomet'] == 0)]
    
    count_high_sdl = (known_sdl['scibert_prob'] > 0.9).sum()
    count_high_background = (background['scibert_prob'] > 0.9).sum()
    
    print(f"  Known SDL ({len(known_sdl):,}): mean={known_sdl['scibert_prob'].mean():.4f}, >0.9: {count_high_sdl:,}")
    print(f"  Background ({len(background):,}): mean={background['scibert_prob'].mean():.4f}, >0.9: {count_high_background:,}")
    
    total_time = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"COMPLETED: Total time {total_time:.2f}s")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()

