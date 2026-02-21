"""
SciBERT SDL Classifier - ITERATION 1 CLEAN
Streamlined version with optional improvements
"""
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import os
import re
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
# CONFIGURATION - CHANGE THESE FOR DIFFERENT RUNS
# ==============================================================================
PROJECT_DIR = "/project/def-kmcel/hridansh/openalex_project"
INPUT_FILE = f"{PROJECT_DIR}/data/regression/test/regression_dataset_subset.csv"

# Output naming - change for each run
OUTPUT_DIR = f"{PROJECT_DIR}/data/scibert_final"
RESULTS_FILE = f"{OUTPUT_DIR}/scores.csv"

# Model
MODEL_NAME = f"{PROJECT_DIR}/data/scibert/training/iteration_1"

# Hyperparameters - MAIN TUNING VARIABLES
MAX_LENGTH = 512
BATCH_SIZE = 16        # Try: 16, 32
EPOCHS = 4            # Try: 4, 5, 6
LEARNING_RATE = 2e-5  # Try: 1e-5, 2e-5, 3e-5
TRAIN_SPLIT = 0.85

# Optional improvements (set to False/0.0/1 to disable)
USE_FOCAL_LOSS = False      # Helps with hard examples
LABEL_SMOOTHING = 0.0       # Reduces overconfidence (try 0.1)
GRAD_ACCUM_STEPS = 1        # Effective batch size = BATCH_SIZE * this

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================================================================
# OPTIONAL: FOCAL LOSS
# ==============================================================================

class FocalLoss(nn.Module):
    """Focal loss - focuses on hard examples"""
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
# TEXT CLEANING
# ==============================================================================

def clean_text(text):
    """Remove metadata artifacts"""
    if pd.isna(text):
        return ""
    
    text = str(text)
    
    # Remove copyright, publishers, URLs, emails, altmetric in one pass
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
# DATA LOADING
# ==============================================================================

def load_and_prepare_data():
    """Load data and create labels"""
    
    print("\n" + "="*70)
    print(f"LOADING DATA ")
    print("="*70)
    
    df = pd.read_csv(INPUT_FILE, low_memory=False).reset_index(drop=True)
    print(f"Total papers: {len(df):,}")
    
    # Clean and combine text
    df['title'] = df['title'].fillna("").apply(clean_text)
    df['abstract'] = df['abstract'].fillna("").apply(clean_text)
    df['text'] = df['title'] + " [SEP] " + df['abstract']
    
    # Create labels
    df['SDL_Brown'] = df['SDL_Brown'].fillna(0).astype(int)
    df['SDL_Tomet'] = df['SDL_Tomet'].fillna(0).astype(int)
    df['label'] = ((df['SDL_Brown'] == 1) | (df['SDL_Tomet'] == 1)).astype(int)
    
    n_pos = df['label'].sum()
    print(f"Positive (SDL): {n_pos:,}")
    print(f"Negative: {(df['label'] == 0).sum():,}")
    
    return df

def create_balanced_dataset(df):
    """Create 1:1 balanced dataset"""
    
    positives = df[df['label'] == 1].copy()
    negatives = df[df['label'] == 0].sample(n=len(positives), random_state=42)

    
    balanced = pd.concat([positives, negatives], ignore_index=True)
    return balanced.sample(frac=1, random_state=42).reset_index(drop=True)

# ==============================================================================
# TOKENIZATION
# ==============================================================================

def tokenize_function(examples, tokenizer):
    return tokenizer(
        examples["text"],
        truncation=True,
        padding="max_length",
        max_length=MAX_LENGTH
    )

# ==============================================================================
# METRICS
# ==============================================================================

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    
    tn, fp, fn, tp = confusion_matrix(labels, predictions).ravel()
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1': f1
    }

# ==============================================================================
# CUSTOM TRAINER (OPTIONAL)
# ==============================================================================

class CustomTrainer(Trainer):
    """Optional: focal loss + label smoothing"""
    
    def __init__(self, *args, use_focal_loss=False, label_smoothing=0.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_focal_loss = use_focal_loss
        self.label_smoothing = label_smoothing
        if use_focal_loss:
            self.focal_loss = FocalLoss()
    
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.get("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        
        # Ensure labels exist
        if labels is None:
            labels = inputs.pop("labels")
        
        if self.use_focal_loss:
            loss = self.focal_loss(logits, labels)
        elif self.label_smoothing > 0:
            loss_fct = nn.CrossEntropyLoss(label_smoothing=self.label_smoothing)
            loss = loss_fct(logits, labels)
        else:
            loss = outputs.loss
        
        # Ensure loss is not None
        if loss is None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits, labels)
        
        return (loss, outputs) if return_outputs else loss

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    
    print("\n" + "="*70)
    print(f"SciBERT SDL CLASSIFIER ")
    print("="*70)
    print(f"LR: {LEARNING_RATE}, BS: {BATCH_SIZE}, Epochs: {EPOCHS}")
    print(f"Focal Loss: {USE_FOCAL_LOSS}, Label Smoothing: {LABEL_SMOOTHING}")
    
    # Load data
    full_df = load_and_prepare_data()
    balanced_df = create_balanced_dataset(full_df)
    
    # Split
    train_df, val_df = train_test_split(
        balanced_df,
        train_size=TRAIN_SPLIT,
        random_state=42,
        stratify=balanced_df['label']
    )
    
    print(f"\nTrain: {len(train_df):,} | Val: {len(val_df):,}")
    
    # Load model
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
    
    # Tokenize
    train_dataset = Dataset.from_pandas(train_df[['text', 'label']])
    val_dataset = Dataset.from_pandas(val_df[['text', 'label']])
    
    train_dataset = train_dataset.map(
        lambda x: tokenize_function(x, tokenizer), batched=True
    )
    val_dataset = val_dataset.map(
        lambda x: tokenize_function(x, tokenizer), batched=True
    )
    
    # Training args
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        num_train_epochs=EPOCHS,
        gradient_accumulation_steps=GRAD_ACCUM_STEPS,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        save_total_limit=1,
        logging_steps=50,
        fp16=True,
        report_to="none",
        seed=42
    )
    
    # Trainer
    trainer = CustomTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
        use_focal_loss=USE_FOCAL_LOSS,
        label_smoothing=LABEL_SMOOTHING
    )
    
    print("\n" + "="*70)
    print("TRAINING")
    print("="*70 + "\n")
    
    trainer.train()
    
    # Validation
    val_results = trainer.evaluate()
    
    print("\n" + "="*70)
    print("VALIDATION RESULTS")
    print("="*70)
    print(f"Precision: {val_results['eval_precision']:.4f}")
    print(f"Recall:    {val_results['eval_recall']:.4f}")
    print(f"F1:        {val_results['eval_f1']:.4f}")
    
    # Save model
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    # Inference
    print("\n" + "="*70)
    print("INFERENCE")
    print("="*70)
    
    full_dataset = Dataset.from_pandas(full_df[['text']])
    full_dataset = full_dataset.map(
        lambda x: tokenize_function(x, tokenizer), batched=True
    )
    
    full_predictions = trainer.predict(full_dataset)
    full_probs = torch.nn.functional.softmax(
        torch.tensor(full_predictions.predictions), dim=-1
    )[:, 1].numpy()
    
    # Save results
    results_df = full_df[[
        'article_id', 'doi', 'title', 'publication_year', 'field',
        'SDL_Brown', 'SDL_Tomet'
    ]].copy()
    
    results_df['scibert_prob'] = full_probs
    results_df.to_csv(RESULTS_FILE, index=False)
    
    # Summary
    known_sdl = results_df[(results_df['SDL_Brown'] == 1) | (results_df['SDL_Tomet'] == 1)]
    background = results_df[(results_df['SDL_Brown'] == 0) & (results_df['SDL_Tomet'] == 0)]
    
    print(f"\nKnown SDL: mean={known_sdl['scibert_prob'].mean():.4f}, >0.9: {(known_sdl['scibert_prob'] > 0.9).sum():,}")
    print(f"Background: mean={background['scibert_prob'].mean():.4f}, >0.9: {(background['scibert_prob'] > 0.9).sum():,}")
    
    print(f"\n✓ Saved: {RESULTS_FILE}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()


# """
# SciBERT SDL Classifier - ITERATION 2
# Improvements:
# 1. Text preprocessing to dilute software/generic optimization signals
# 2. Stratified negative sampling (50% random + 50% CS/Engineering)
# 3. Increased learning rate (3e-5), more epochs (6), label smoothing (0.1)
# 4. Custom loss weighting (FP penalty > FN penalty)
# """
# import pandas as pd
# import numpy as np
# import torch
# import torch.nn as nn
# import os
# import re
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import confusion_matrix
# from transformers import (
#     AutoTokenizer, 
#     AutoModelForSequenceClassification, 
#     Trainer, 
#     TrainingArguments,
#     DataCollatorWithPadding
# )
# from datasets import Dataset

# # ==============================================================================
# # CONFIGURATION
# # ==============================================================================
# PROJECT_DIR = "/project/def-kmcel/hridansh/openalex_project"
# INPUT_FILE = f"{PROJECT_DIR}/data/regression/test/regression_dataset_subset.csv"

# # Iteration 2 outputs
# OUTPUT_DIR = f"{PROJECT_DIR}/data/scibert_final/2"
# RESULTS_FILE = f"{OUTPUT_DIR}/scores.csv"

# MODEL_NAME = f"{PROJECT_DIR}/data/scibert/training/iteration_1"

# # ITERATION 2 HYPERPARAMETERS
# MAX_LENGTH = 512
# BATCH_SIZE = 16
# EPOCHS = 6              # Was 4 - more epochs for hard examples
# LEARNING_RATE = 3e-5    # Was 2e-5 - slightly more aggressive
# TRAIN_SPLIT = 0.85      # Was 0.85 - more validation data
# LABEL_SMOOTHING = 0.1   # Was 0.0 - reduce overconfidence
# GRAD_ACCUM_STEPS = 1
# FP_PENALTY_WEIGHT = 10  # False positive penalty multiplier

# os.makedirs(OUTPUT_DIR, exist_ok=True)

# # ==============================================================================
# # TEXT PREPROCESSING - DILUTE PROBLEMATIC SIGNALS
# # ==============================================================================

# def dilute_generic_signals(text):
#     """
#     Replace overly generic terms with neutral tokens to force model 
#     to learn from context rather than keyword matching.
#     """
#     if pd.isna(text):
#         return ""
    
#     text = str(text).lower()
    
#     # Software/tooling terms that are too generic
#     software_patterns = [
#         (r'\bpython library\b', '[SOFTWARE_TOOL]'),
#         (r'\bpython package\b', '[SOFTWARE_TOOL]'),
#         (r'\bopen source python\b', '[SOFTWARE_TOOL]'),
#         (r'\bopen source software\b', '[SOFTWARE_TOOL]'),
#         (r'\bweb application\b', '[SOFTWARE_TOOL]'),
#         (r'\bweb server\b', '[SOFTWARE_TOOL]'),
#         (r'\bgraphical user interface\b', '[SOFTWARE_TOOL]'),
#         (r'\bsoftware package\b', '[SOFTWARE_TOOL]'),
#         (r'\bsoftware tool\b', '[SOFTWARE_TOOL]'),
#         (r'\bcode generation\b', '[SOFTWARE_TOOL]'),
#         (r'\bprogramming language\b', '[SOFTWARE_TOOL]'),
#     ]
    
#     # Generic optimization terms (keep domain-specific ones)
#     optimization_patterns = [
#         (r'\bevolutionary optimization\b', '[OPTIMIZATION_METHOD]'),
#         (r'\bevolutionary algorithm\b', '[OPTIMIZATION_METHOD]'),
#         (r'\bgenetic algorithm\b', '[OPTIMIZATION_METHOD]'),
#         (r'\brandom search\b', '[OPTIMIZATION_METHOD]'),
#         (r'\bglobal optimization\b', '[OPTIMIZATION_METHOD]'),
#     ]
    
#     # Apply replacements
#     for pattern, replacement in software_patterns + optimization_patterns:
#         text = re.sub(pattern, replacement, text)
    
#     return text

# def clean_text(text):
#     """Remove metadata artifacts (keep from iteration 1)"""
#     if pd.isna(text):
#         return ""
    
#     text = str(text)
    
#     # Remove copyright, publishers, URLs, emails, altmetric
#     patterns = [
#         r'©\s*\d{4}', r'copyright\s+\d{4}',
#         r'elsevier|wiley|springer|nature publishing|american chemical society|royal society of chemistry',
#         r'http[s]?://\S+', r'www\.\S+', r'doi:\s*\S+', r'\S+@\S+',
#         r'altmetric\s*\d+',
#         r'all rights reserved|supplementary material|supporting information'
#     ]
    
#     for pattern in patterns:
#         text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
#     return re.sub(r'\s+', ' ', text).strip()



# # ==============================================================================
# # DATA LOADING
# # ==============================================================================

# def load_and_prepare_data():
#     """Load data and create labels"""
    
#     print("\n" + "="*70)
#     print("LOADING DATA")
#     print("="*70)
    
#     df = pd.read_csv(INPUT_FILE, low_memory=False).reset_index(drop=True)
#     print(f"Total papers: {len(df):,}")
    
#     # Clean text
#     df['title'] = df['title'].fillna("").apply(clean_text)
#     df['abstract'] = df['abstract'].fillna("").apply(clean_text)
    
#     # ITERATION 2: Dilute generic signals
#     print("\nDiluting generic software/optimization signals...")
#     df['abstract_processed'] = df['abstract'].apply(dilute_generic_signals)
    
#     # Combine (use processed abstract)
#     df['text'] = df['title'] + " [SEP] " + df['abstract_processed']
    
#     # Create labels
#     df['SDL_Brown'] = df['SDL_Brown'].fillna(0).astype(int)
#     df['SDL_Tomet'] = df['SDL_Tomet'].fillna(0).astype(int)
#     df['label'] = ((df['SDL_Brown'] == 1) | (df['SDL_Tomet'] == 1)).astype(int)
    
#     n_pos = df['label'].sum()
#     print(f"\nPositive (SDL): {n_pos:,}")
#     print(f"Negative: {(df['label'] == 0).sum():,}")
    
#     return df

# def create_balanced_dataset_v2(df):
#     """
#     ITERATION 2: Stratified negative sampling
#     - 50% random negatives (broad coverage)
#     - 50% from CS + Engineering (SDL-adjacent)
#     """
    
#     print("\n" + "="*70)
#     print("CREATING BALANCED DATASET (ITERATION 2 STRATEGY)")
#     print("="*70)
    
#     positives = df[df['label'] == 1].copy()
#     n_pos = len(positives)
#     print(f"\nPositives: {n_pos:,}")
    
#     all_negatives = df[df['label'] == 0].copy()
    
#     # Target: same number of negatives as positives
#     n_neg_target = n_pos
    
#     # Stratified sampling: 50% random, 50% CS+Engineering
#     n_random = int(0.5 * n_neg_target)
#     n_cs_eng = n_neg_target - n_random
    
#     print(f"\nNegative sampling strategy:")
#     print(f"  CS + Engineering papers: {n_cs_eng:,} (50%)")
#     print(f"  Random (all fields): {n_random:,} (50%)")
    
#     # Sample CS + Engineering
#     cs_eng_negatives = all_negatives[
#         all_negatives['field'].isin(['Computer Science', 'Engineering'])
#     ]
#     if len(cs_eng_negatives) >= n_cs_eng:
#         sampled_cs_eng = cs_eng_negatives.sample(n=n_cs_eng, random_state=42)
#     else:
#         print(f"  ⚠ Only {len(cs_eng_negatives):,} CS+Eng papers available, using all")
#         sampled_cs_eng = cs_eng_negatives
#         n_random += (n_cs_eng - len(cs_eng_negatives))  # Add remainder to random
    
#     # Sample random from remaining
#     remaining_negatives = all_negatives[
#         ~all_negatives['article_id'].isin(sampled_cs_eng['article_id'])
#     ]
#     sampled_random = remaining_negatives.sample(
#         n=min(n_random, len(remaining_negatives)), 
#         random_state=42
#     )
    
#     # Combine negatives
#     negatives = pd.concat([sampled_cs_eng, sampled_random], ignore_index=True)
    
#     print(f"\nTotal negatives: {len(negatives):,}")
#     print(f"  By field:")
#     for field in negatives['field'].value_counts().head(5).items():
#         print(f"    {field[0]}: {field[1]:,}")
    
#     # Combine and shuffle
#     balanced = pd.concat([positives, negatives], ignore_index=True)
#     balanced = balanced.sample(frac=1, random_state=42).reset_index(drop=True)
    
#     print(f"\n✓ Final balanced dataset: {len(balanced):,} papers")
#     print(f"  Positive: {(balanced['label'] == 1).sum():,}")
#     print(f"  Negative: {(balanced['label'] == 0).sum():,}")
    
#     return balanced

# # ==============================================================================
# # CUSTOM TRAINER WITH FP PENALTY
# # ==============================================================================

# class WeightedLossTrainer(Trainer):
#     """
#     Custom trainer with:
#     - Label smoothing (reduces overconfidence)
#     - FP penalty weighting (penalize false positives more than false negatives)
#     """
    
#     def __init__(self, *args, label_smoothing=0.0, fp_weight=1.0, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.label_smoothing = label_smoothing
#         self.fp_weight = fp_weight
    
#     def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
#         labels = inputs.pop("labels")
#         outputs = model(**inputs)
#         logits = outputs.logits
        
#         # Simple cross entropy loss with label smoothing (no reduction yet)
#         # Label smoothing is handled by pytorch internally, no device issues
#         if self.label_smoothing > 0:
#             loss_fct = nn.CrossEntropyLoss(label_smoothing=self.label_smoothing, reduction='none')
#         else:
#             loss_fct = nn.CrossEntropyLoss(reduction='none')
        
#         loss_per_sample = loss_fct(logits, labels)
        
#         # Apply FP weighting if needed
#         if self.fp_weight != 1.0:
#             with torch.no_grad():  # Don't track gradients for mask computation
#                 predictions = torch.argmax(logits, dim=-1)
#                 # False positives: predicted=1, actual=0
#                 fp_mask = (predictions == 1) & (labels == 0)
            
#             # Create weights on same device as loss
#             weights = torch.ones(loss_per_sample.size(0), device=logits.device)
#             weights[fp_mask] = self.fp_weight
            
#             weighted_loss = (loss_per_sample * weights).mean()
#         else:
#             weighted_loss = loss_per_sample.mean()
        
#         return (weighted_loss, outputs) if return_outputs else weighted_loss


# # ==============================================================================
# # TOKENIZATION & METRICS (unchanged)
# # ==============================================================================

# def tokenize_function(examples, tokenizer):
#     return tokenizer(
#         examples["text"],
#         truncation=True,
#         padding="max_length",
#         max_length=MAX_LENGTH
#     )

# def compute_metrics(eval_pred):
#     predictions, labels = eval_pred
#     predictions = np.argmax(predictions, axis=1)
    
#     tn, fp, fn, tp = confusion_matrix(labels, predictions).ravel()
    
#     precision = tp / (tp + fp) if (tp + fp) > 0 else 0
#     recall = tp / (tp + fn) if (tp + fn) > 0 else 0
#     f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
#     return {
#         'precision': precision,
#         'recall': recall,
#         'f1': f1,
#         'fp_count': int(fp),
#         'fn_count': int(fn)
#     }

# # ==============================================================================
# # MAIN
# # ==============================================================================

# def main():
    
#     print("\n" + "="*70)
#     print("SciBERT SDL CLASSIFIER - ITERATION 2")
#     print("="*70)
#     print("\nKey improvements:")
#     print("  • Text preprocessing to dilute software/optimization signals")
#     print("  • Stratified negative sampling (50% random + 50% CS/Eng)")
#     print("  • Increased LR (3e-5), more epochs (6), label smoothing (0.1)")
#     print(f"  • FP penalty weighting ({FP_PENALTY_WEIGHT}x)")
#     print()
#     print(f"Hyperparameters:")
#     print(f"  LR: {LEARNING_RATE}, BS: {BATCH_SIZE}, Epochs: {EPOCHS}")
#     print(f"  Label Smoothing: {LABEL_SMOOTHING}, Train Split: {TRAIN_SPLIT}")
    
#     # Load data
#     full_df = load_and_prepare_data()
#     balanced_df = create_balanced_dataset_v2(full_df)
    
#     # Split
#     train_df, val_df = train_test_split(
#         balanced_df,
#         train_size=TRAIN_SPLIT,
#         random_state=42,
#         stratify=balanced_df['label']
#     )
    
#     print(f"\nTrain: {len(train_df):,} | Val: {len(val_df):,}")
    
#     # Load model
#     print("\n" + "="*70)
#     print("LOADING MODEL")
#     print("="*70)
#     tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
#     model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
#     print("✓ Model loaded")
    
#     # Tokenize
#     print("\nTokenizing...")
#     train_dataset = Dataset.from_pandas(train_df[['text', 'label']])
#     val_dataset = Dataset.from_pandas(val_df[['text', 'label']])
    
#     train_dataset = train_dataset.map(
#         lambda x: tokenize_function(x, tokenizer), batched=True
#     )
#     val_dataset = val_dataset.map(
#         lambda x: tokenize_function(x, tokenizer), batched=True
#     )
#     print("✓ Tokenization complete")
    
#     # Training args
#     training_args = TrainingArguments(
#         output_dir=OUTPUT_DIR,
#         eval_strategy="epoch",
#         save_strategy="epoch",
#         learning_rate=LEARNING_RATE,
#         per_device_train_batch_size=BATCH_SIZE,
#         per_device_eval_batch_size=BATCH_SIZE,
#         num_train_epochs=EPOCHS,
#         gradient_accumulation_steps=GRAD_ACCUM_STEPS,
#         weight_decay=0.01,
#         load_best_model_at_end=True,
#         metric_for_best_model="f1",
#         save_total_limit=1,
#         logging_steps=50,
#         fp16=True,
#         report_to="none",
#         seed=42
#     )
    
#     # Trainer with custom loss
#     trainer = WeightedLossTrainer(
#         model=model,
#         args=training_args,
#         train_dataset=train_dataset,
#         eval_dataset=val_dataset,
#         data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
#         compute_metrics=compute_metrics,
#         label_smoothing=LABEL_SMOOTHING,
#         fp_weight=FP_PENALTY_WEIGHT
#     )
    
#     print("\n" + "="*70)
#     print("TRAINING")
#     print("="*70 + "\n")
    
#     trainer.train()
    
#     # Validation
#     print("\n" + "="*70)
#     print("VALIDATION RESULTS")
#     print("="*70)
#     val_results = trainer.evaluate()
    
#     print(f"Precision: {val_results['eval_precision']:.4f}")
#     print(f"Recall:    {val_results['eval_recall']:.4f}")
#     print(f"F1:        {val_results['eval_f1']:.4f}")
#     print(f"FP count:  {val_results['eval_fp_count']:,}")
#     print(f"FN count:  {val_results['eval_fn_count']:,}")
    
#     # Save model
#     print("\n" + "="*70)
#     print("SAVING MODEL")
#     print("="*70)
#     trainer.save_model(OUTPUT_DIR)
#     tokenizer.save_pretrained(OUTPUT_DIR)
#     print(f"✓ Model saved to {OUTPUT_DIR}")
    
#     # Inference on full dataset
#     print("\n" + "="*70)
#     print("INFERENCE ON FULL DATASET")
#     print("="*70)
    
#     full_dataset = Dataset.from_pandas(full_df[['text']])
#     full_dataset = full_dataset.map(
#         lambda x: tokenize_function(x, tokenizer), batched=True
#     )
    
#     print("Running inference...")
#     full_predictions = trainer.predict(full_dataset)
#     full_probs = torch.nn.functional.softmax(
#         torch.tensor(full_predictions.predictions), dim=-1
#     )[:, 1].numpy()
    
#     # Save results
#     results_df = full_df[[
#         'article_id', 'doi', 'title', 'publication_year', 'field',
#         'SDL_Brown', 'SDL_Tomet'
#     ]].copy()
    
#     results_df['scibert_prob_iter2'] = full_probs
#     results_df.to_csv(RESULTS_FILE, index=False)
    
#     print(f"✓ Saved scores to {RESULTS_FILE}")
    
#     # Summary statistics
#     print("\n" + "="*70)
#     print("SUMMARY STATISTICS")
#     print("="*70)
    
#     known_sdl = results_df[
#         (results_df['SDL_Brown'] == 1) | (results_df['SDL_Tomet'] == 1)
#     ]
#     background = results_df[
#         (results_df['SDL_Brown'] == 0) & (results_df['SDL_Tomet'] == 0)
#     ]
    
#     print(f"\nKnown SDL papers (n={len(known_sdl):,}):")
#     print(f"  Mean score: {known_sdl['scibert_prob_iter2'].mean():.4f}")
#     print(f"  Median score: {known_sdl['scibert_prob_iter2'].median():.4f}")
#     print(f"  >0.9: {(known_sdl['scibert_prob_iter2'] > 0.9).sum():,} ({(known_sdl['scibert_prob_iter2'] > 0.9).sum() / len(known_sdl) * 100:.1f}%)")
#     print(f"  >0.8: {(known_sdl['scibert_prob_iter2'] > 0.8).sum():,} ({(known_sdl['scibert_prob_iter2'] > 0.8).sum() / len(known_sdl) * 100:.1f}%)")
    
#     print(f"\nBackground papers (n={len(background):,}):")
#     print(f"  Mean score: {background['scibert_prob_iter2'].mean():.4f}")
#     print(f"  >0.9: {(background['scibert_prob_iter2'] > 0.9).sum():,}")
#     print(f"  >0.8: {(background['scibert_prob_iter2'] > 0.8).sum():,}")
    
#     print(f"\nBy field:")
#     for field in results_df['field'].unique():
#         field_df = results_df[results_df['field'] == field]
#         mean_score = field_df['scibert_prob_iter2'].mean()
#         high_conf = (field_df['scibert_prob_iter2'] > 0.9).sum()
#         print(f"  {field:25}: mean={mean_score:.4f}, >0.9: {high_conf:>6,}")
    
#     print("\n" + "="*70)
#     print("ITERATION 2 COMPLETE")
#     print("="*70)
#     print(f"\nCompare with iteration 1:")
#     print(f"  Iter 1: 29,524 papers >0.9")
#     print(f"  Iter 2: {(background['scibert_prob_iter2'] > 0.9).sum():,} papers >0.9")
#     print(f"  Reduction: {29524 - (background['scibert_prob_iter2'] > 0.9).sum():,} papers")
#     print()

# if __name__ == "__main__":
#     main()

# """
# SciBERT SDL Classifier - ITERATION 1 ANALYSIS
# Fixed version with deduplication and validation
# """
# import pandas as pd
# import numpy as np  
# from sklearn.feature_extraction.text import CountVectorizer
# import os

# # ==============================================================================
# # CONFIGURATION
# # ==============================================================================
# PROJECT_DIR = "/project/def-kmcel/hridansh/openalex_project"

# SCORES_FILE = f"{PROJECT_DIR}/data/scibert_final/scores.csv"
# FULL_DATA_FILE = f"{PROJECT_DIR}/data/regression/test/regression_dataset_subset.csv"
# OUTPUT_DIR = f"{PROJECT_DIR}/data/scibert_final/1"

# os.makedirs(OUTPUT_DIR, exist_ok=True)

# # ==============================================================================
# # LOAD AND VALIDATE DATA
# # ==============================================================================

# print("\n" + "="*70)
# print("LOADING & VALIDATING DATA")
# print("="*70)

# if not os.path.exists(SCORES_FILE):
#     print(f"ERROR: Scores file not found at {SCORES_FILE}")
#     exit(1)

# # Load scores
# df_raw = pd.read_csv(SCORES_FILE)
# print(f"\nRaw scores file: {len(df_raw):,} rows")

# # Check for duplicates
# duplicates = df_raw.duplicated(subset=['article_id'], keep=False)
# n_duplicates = duplicates.sum()

# if n_duplicates > 0:
#     print(f"WARNING: Found {n_duplicates:,} duplicate rows!")
#     print(f"  Unique article_ids: {df_raw['article_id'].nunique():,}")
#     print(f"  Deduplicating by article_id (keeping first occurrence)...")
#     df = df_raw.drop_duplicates(subset=['article_id'], keep='first').reset_index(drop=True)
#     print(f"  After deduplication: {len(df):,} papers")
# else:
#     df = df_raw.copy()
#     print(f"No duplicates found - data is clean")

# # Verify score column
# score_col = 'scibert_prob'
# if score_col not in df.columns:
#     print(f"\nERROR: Expected column '{score_col}' not found")
#     print(f"Available columns: {list(df.columns)}")
#     exit(1)

# # Load text data if needed
# needs_text = ('title' not in df.columns) or ('abstract' not in df.columns)

# if needs_text:
#     print(f"\nLoading text from: {FULL_DATA_FILE}")
#     df_full = pd.read_csv(FULL_DATA_FILE, low_memory=False)
    
#     # Merge only needed columns
#     merge_cols = ['article_id']
#     if 'title' not in df.columns:
#         merge_cols.append('title')
#     if 'abstract' not in df.columns:
#         merge_cols.append('abstract')
    
#     df = pd.merge(df, df_full[merge_cols], on='article_id', how='left')

# # Prepare text
# has_text = ('title' in df.columns) and ('abstract' in df.columns)
# if has_text:
#     df['title'] = df['title'].fillna("")
#     df['abstract'] = df['abstract'].fillna("")
#     df['full_text'] = df['title'] + " " + df['abstract']
# else:
#     print("\nWARNING: No text data available")
#     df['full_text'] = ""

# # Create ground truth labels
# df['SDL_Brown'] = df['SDL_Brown'].fillna(0).astype(int)
# df['SDL_Tomet'] = df['SDL_Tomet'].fillna(0).astype(int)
# df['label_true'] = ((df['SDL_Brown'] == 1) | (df['SDL_Tomet'] == 1)).astype(int)

# # Validate counts
# n_brown = (df['SDL_Brown'] == 1).sum()
# n_tomet = (df['SDL_Tomet'] == 1).sum()
# n_both = ((df['SDL_Brown'] == 1) & (df['SDL_Tomet'] == 1)).sum()
# n_sdl = (df['label_true'] == 1).sum()

# print(f"\n{'='*70}")
# print("DATA VALIDATION")
# print(f"{'='*70}")
# print(f"Total papers:     {len(df):,}")
# print(f"SDL_Brown only:   {n_brown - n_both:,}")
# print(f"SDL_Tomet only:   {n_tomet - n_both:,}")
# print(f"Both sources:     {n_both:,}")
# print(f"Total known SDL:  {n_sdl:,}")
# print(f"Background:       {(df['label_true'] == 0).sum():,}")

# # Sanity check
# expected_sdl = n_brown + n_tomet - n_both
# if n_sdl != expected_sdl:
#     print(f"\nWARNING: SDL count mismatch!")
#     print(f"  Computed: {n_sdl}, Expected: {expected_sdl}")

# # ==============================================================================
# # 1. SCORE DISTRIBUTION
# # ==============================================================================

# print("\n" + "="*70)
# print("1. SCORE DISTRIBUTION")
# print("="*70)

# print(f"\nOverall Statistics:")
# print(f"  Mean:   {df[score_col].mean():.4f}")
# print(f"  Median: {df[score_col].median():.4f}")
# print(f"  Std:    {df[score_col].std():.4f}")
# print(f"  Min:    {df[score_col].min():.4f}")
# print(f"  Max:    {df[score_col].max():.4f}")

# print(f"\nScore Buckets:")
# buckets = [
#     (0.00, 0.10, "Very Low"),
#     (0.10, 0.30, "Low"),
#     (0.30, 0.50, "Medium-Low"),
#     (0.50, 0.70, "Medium-High"),
#     (0.70, 0.90, "High"),
#     (0.90, 1.00, "Very High")
# ]

# for low, high, label in buckets:
#     count = ((df[score_col] >= low) & (df[score_col] < high)).sum()
#     pct = count / len(df) * 100
#     print(f"  {label:15} [{low:.2f}-{high:.2f}): {count:>7,} ({pct:>5.2f}%)")

# # ==============================================================================
# # 2. KNOWN SDL RECALL
# # ==============================================================================

# print("\n" + "="*70)
# print("2. KNOWN SDL RECALL")
# print("="*70)

# known_sdl = df[df['label_true'] == 1].copy()
# background = df[df['label_true'] == 0].copy()

# print(f"\nKnown SDL Papers: {len(known_sdl):,}")
# print(f"  Brown only: {((known_sdl['SDL_Brown'] == 1) & (known_sdl['SDL_Tomet'] == 0)).sum():,}")
# print(f"  Tomet only: {((known_sdl['SDL_Brown'] == 0) & (known_sdl['SDL_Tomet'] == 1)).sum():,}")
# print(f"  Both:       {((known_sdl['SDL_Brown'] == 1) & (known_sdl['SDL_Tomet'] == 1)).sum():,}")

# print(f"\nScore Statistics (Known SDL):")
# print(f"  Mean:   {known_sdl[score_col].mean():.4f}")
# print(f"  Median: {known_sdl[score_col].median():.4f}")
# print(f"  Min:    {known_sdl[score_col].min():.4f}")

# print(f"\nRecall at Thresholds:")
# for thresh in [0.5, 0.7, 0.9, 0.95]:
#     recalled = (known_sdl[score_col] >= thresh).sum()
#     recall_rate = recalled / len(known_sdl) * 100
#     print(f"  >= {thresh:.2f}: {recalled:>4}/{len(known_sdl):>4} ({recall_rate:>5.1f}%)")

# # Save hard misses
# hard_misses = known_sdl[known_sdl[score_col] < 0.20].copy()
# print(f"\nHard Misses (score < 0.20): {len(hard_misses)}")
# if len(hard_misses) > 0:
#     print(f"  Brown only: {((hard_misses['SDL_Brown'] == 1) & (hard_misses['SDL_Tomet'] == 0)).sum()}")
#     print(f"  Tomet only: {((hard_misses['SDL_Brown'] == 0) & (hard_misses['SDL_Tomet'] == 1)).sum()}")
#     print(f"  Both:       {((hard_misses['SDL_Brown'] == 1) & (hard_misses['SDL_Tomet'] == 1)).sum()}")
    
#     hard_misses_path = f"{OUTPUT_DIR}/hard_misses.csv"
#     hard_misses[['article_id', 'doi', 'title', score_col, 'SDL_Brown', 'SDL_Tomet']].to_csv(
#         hard_misses_path, index=False
#     )
#     print(f"  ✓ Saved: {hard_misses_path}")

# # ==============================================================================
# # 3. FALSE POSITIVE ANALYSIS
# # ==============================================================================

# print("\n" + "="*70)
# print("3. FALSE POSITIVE ANALYSIS")
# print("="*70)

# print(f"\nBackground Papers: {len(background):,}")
# print(f"  Mean Score: {background[score_col].mean():.4f}")
# print(f"  Median:     {background[score_col].median():.4f}")
# print(f"  Max:        {background[score_col].max():.4f}")

# print(f"\nPotential False Positives:")
# for thresh in [0.5, 0.7, 0.9, 0.95]:
#     fp_count = (background[score_col] >= thresh).sum()
#     fp_rate = fp_count / len(background) * 100
#     print(f"  >= {thresh:.2f}: {fp_count:>7,} ({fp_rate:>5.2f}%)")

# # ==============================================================================
# # 4. FIELD-SPECIFIC PATTERNS
# # ==============================================================================

# print("\n" + "="*70)
# print("4. FIELD-SPECIFIC PATTERNS")
# print("="*70)

# print(f"\nScores by Field:")
# for field in sorted(df['field'].unique()):
#     field_df = df[df['field'] == field]
#     avg_score = field_df[score_col].mean()
#     high_conf = (field_df[score_col] > 0.9).sum()
#     known_sdl_count = (field_df['label_true'] == 1).sum()
#     print(f"  {field:25}: avg={avg_score:.4f}  |  >0.9: {high_conf:>6,}  |  known SDL: {known_sdl_count:>4}")

# # ==============================================================================
# # 5. DISTINCTIVE VOCABULARY (LOG-ODDS)
# # ==============================================================================

# print("\n" + "="*70)
# print("5. DISTINCTIVE VOCABULARY")
# print("="*70)

# if not has_text:
#     print("\n  ⚠ Skipping (no text data)")
# else:
#     high_conf = df[df[score_col] > 0.90].copy()
#     low_conf = df[df[score_col] < 0.10].copy()
    
#     print(f"\nHigh confidence (>0.90): {len(high_conf):,}")
#     print(f"Low confidence (<0.10):  {len(low_conf):,}")
    
#     if len(high_conf) >= 10 and len(low_conf) >= 10:
#         subset = pd.concat([high_conf, low_conf])
#         y = np.where(subset[score_col] > 0.90, 1, 0)
        
#         vec = CountVectorizer(
#             ngram_range=(2, 3), 
#             stop_words='english', 
#             min_df=5, 
#             max_features=50000
#         )
        
#         try:
#             X = vec.fit_transform(subset['full_text'])
#             X_pos = X[y == 1]
#             X_neg = X[y == 0]
            
#             pos_counts = np.array(X_pos.sum(axis=0)).flatten() + 1
#             neg_counts = np.array(X_neg.sum(axis=0)).flatten() + 1
            
#             pos_norm = pos_counts / pos_counts.sum()
#             neg_norm = neg_counts / neg_counts.sum()
#             log_odds = np.log(pos_norm / neg_norm)
            
#             vocab = {v: k for k, v in vec.vocabulary_.items()}
            
#             print("\nTop 30 Phrases (HIGH scores):")
#             for idx in log_odds.argsort()[::-1][:30]:
#                 print(f"  + {vocab[idx]:40} ({log_odds[idx]:>6.2f})")
            
#             print("\nTop 30 Phrases (LOW scores):")
#             for idx in log_odds.argsort()[:30]:
#                 print(f"  - {vocab[idx]:40} ({log_odds[idx]:>6.2f})")
            
#             logodds_df = pd.DataFrame({
#                 'phrase': [vocab[i] for i in range(len(vocab))],
#                 'log_odds': log_odds
#             }).sort_values('log_odds', ascending=False)
            
#             logodds_path = f"{OUTPUT_DIR}/log_odds_analysis.csv"
#             logodds_df.to_csv(logodds_path, index=False)
#             print(f"\n  ✓ Saved: {logodds_path}")
            
#         except Exception as e:
#             print(f"\n  ✗ Failed: {e}")
#     else:
#         print("\n  ⚠ Insufficient data")

# # ==============================================================================
# # 6. KEYWORD CHECKS
# # ==============================================================================

# print("\n" + "="*70)
# print("6. KEYWORD CHECKS")
# print("="*70)

# if not has_text:
#     print("\n  ⚠ Skipping (no text data)")
# else:
#     print("\n[Robotics Leak]")
#     for kw in ['drone', 'uav', 'autonomous vehicle', 'traffic', 'pedestrian', 'robot']:
#         mask = df['full_text'].str.lower().str.contains(kw, na=False)
#         if mask.sum() > 0:
#             print(f"  {kw:20}: {mask.sum():>6} papers, avg={df[mask][score_col].mean():.4f}, >0.9: {(df[mask][score_col] > 0.9).sum():>5}")
    
#     print("\n[Simulation Trap]")
#     for kw in ['dft', 'density functional', 'molecular dynamics', 'vasp', 'gaussian', 'monte carlo']:
#         mask = df['full_text'].str.lower().str.contains(kw, na=False)
#         if mask.sum() > 0:
#             print(f"  {kw:20}: {mask.sum():>6} papers, avg={df[mask][score_col].mean():.4f}, >0.9: {(df[mask][score_col] > 0.9).sum():>5}")
    
#     print("\n[Topic Confounding]")
#     for kw in ['battery', 'perovskite', 'solar cell', 'photovoltaic', 'catalyst']:
#         mask = df['full_text'].str.lower().str.contains(kw, na=False)
#         if mask.sum() > 0:
#             print(f"  {kw:20}: {mask.sum():>6} papers, avg={df[mask][score_col].mean():.4f}, >0.9: {(df[mask][score_col] > 0.9).sum():>5}")
    
#     print("\n[SDL Indicators]")
#     for kw in ['microfluidic', 'flow chemistry', 'automated synthesis', 'high throughput', 'screening platform']:
#         mask = df['full_text'].str.lower().str.contains(kw, na=False)
#         if mask.sum() > 0:
#             print(f"  {kw:20}: {mask.sum():>6} papers, avg={df[mask][score_col].mean():.4f}, >0.9: {(df[mask][score_col] > 0.9).sum():>5}")

# # ==============================================================================
# # 7. EXPORTS
# # ==============================================================================

# print("\n" + "="*70)
# print("7. EXPORTS")
# print("="*70)

# # Top 100 (deduplicated)
# top_100 = df.nlargest(100, score_col).drop_duplicates(subset=['article_id']).head(100)
# top_100_path = f"{OUTPUT_DIR}/top_100_overall.csv"

# export_cols = ['article_id', 'doi', score_col, 'label_true', 'field', 'SDL_Brown', 'SDL_Tomet']
# if 'title' in df.columns:
#     export_cols.insert(2, 'title')

# top_100[export_cols].to_csv(top_100_path, index=False)
# print(f"  ✓ Top 100: {top_100_path}")

# # Summary
# summary = {
#     'Total Papers': len(df),
#     'Known SDL': n_sdl,
#     'Brown only': n_brown - n_both,
#     'Tomet only': n_tomet - n_both,
#     'Both sources': n_both,
#     'High Confidence (>0.9)': int((df[score_col] > 0.9).sum()),
#     'Known SDL Recall @0.9': f"{(known_sdl[score_col] > 0.9).sum() / len(known_sdl) * 100:.1f}%",
#     'Mean Score (All)': f"{df[score_col].mean():.4f}",
#     'Mean Score (Known SDL)': f"{known_sdl[score_col].mean():.4f}",
#     'Mean Score (Background)': f"{background[score_col].mean():.4f}"
# }

# summary_df = pd.DataFrame([summary]).T
# summary_df.columns = ['Value']
# summary_path = f"{OUTPUT_DIR}/summary_statistics.csv"
# summary_df.to_csv(summary_path)
# print(f"  ✓ Summary: {summary_path}")

# # ==============================================================================
# # DIAGNOSTICS
# # ==============================================================================

# print("\n" + "="*70)
# print("DIAGNOSTICS")
# print("="*70)
# print("\nKey Flags:")
# print(f"  1. >50k papers scoring >0.9?           {'RED FLAG' if (df[score_col] > 0.9).sum() > 50000 else 'OK'}")
# print(f"  2. Known SDL recall @0.9 >75%?         {'GOOD' if (known_sdl[score_col] > 0.9).sum() / len(known_sdl) > 0.75 else 'NEEDS WORK'}")
# print(f"  3. Log-odds show SDL terms?            {'Check log_odds file' if has_text else 'N/A'}")

# print("\n" + "="*70 + "\n")


##2nd part analysis
"""
SciBERT SDL Classifier - COMPREHENSIVE PERFORMANCE ANALYSIS
Sensitivity/Specificity Analysis + Threshold Exploration
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import (
    confusion_matrix, precision_recall_curve, roc_curve, auc,
    classification_report, precision_recall_fscore_support
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================
PROJECT_DIR = "/project/def-kmcel/hridansh/openalex_project"

SCORES_FILE = f"{PROJECT_DIR}/data/scibert_final/1/scores.csv"
OUTPUT_DIR = f"{PROJECT_DIR}/data/scibert_final/1"

# Load data
print("\n" + "="*70)
print("LOADING DATA")
print("="*70)

df = pd.read_csv(SCORES_FILE)
print(f"Loaded {len(df):,} papers")

# Create ground truth labels
df['SDL_Brown'] = df['SDL_Brown'].fillna(0).astype(int)
df['SDL_Tomet'] = df['SDL_Tomet'].fillna(0).astype(int)
df['label_true'] = ((df['SDL_Brown'] == 1) | (df['SDL_Tomet'] == 1)).astype(int)

score_col = 'scibert_prob_iter2'

print(f"\nGround Truth:")
print(f"  Known SDL (label=1): {(df['label_true'] == 1).sum():,}")
print(f"  Background (label=0): {(df['label_true'] == 0).sum():,}")

# ==============================================================================
# 1. THRESHOLD SENSITIVITY ANALYSIS
# ==============================================================================

print("\n" + "="*70)
print("1. THRESHOLD SENSITIVITY ANALYSIS")
print("="*70)

thresholds = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]

print(f"\n{'Threshold':>10} | {'Precision':>10} | {'Recall':>10} | {'F1':>10} | {'Predicted SDL':>15} | {'FP':>10} | {'FN':>10}")
print("-" * 95)

results = []

for thresh in thresholds:
    # Classify
    predictions = (df[score_col] >= thresh).astype(int)
    
    # Calculate metrics
    tn, fp, fn, tp = confusion_matrix(df['label_true'], predictions).ravel()
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    predicted_sdl = predictions.sum()
    
    print(f"{thresh:>10.2f} | {precision:>10.4f} | {recall:>10.4f} | {f1:>10.4f} | {predicted_sdl:>15,} | {fp:>10,} | {fn:>10,}")
    
    results.append({
        'threshold': thresh,
        'precision': precision,
        'recall': recall,
        'specificity': specificity,
        'f1': f1,
        'predicted_sdl': predicted_sdl,
        'true_positives': tp,
        'false_positives': fp,
        'false_negatives': fn,
        'true_negatives': tn
    })

results_df = pd.DataFrame(results)
results_df.to_csv(f"{OUTPUT_DIR}/threshold_analysis.csv", index=False)
print(f"\n✓ Saved to: {OUTPUT_DIR}/threshold_analysis.csv")

# ==============================================================================
# 2. DETAILED PERFORMANCE AT KEY THRESHOLDS
# ==============================================================================

print("\n" + "="*70)
print("2. DETAILED PERFORMANCE AT KEY THRESHOLDS")
print("="*70)

key_thresholds = [0.7, 0.8, 0.9]

for thresh in key_thresholds:
    print(f"\n{'='*70}")
    print(f"THRESHOLD = {thresh:.2f}")
    print(f"{'='*70}")
    
    predictions = (df[score_col] >= thresh).astype(int)
    
    # Full classification report
    print("\nClassification Report:")
    print(classification_report(
        df['label_true'], 
        predictions, 
        target_names=['Non-SDL', 'SDL'],
        digits=4
    ))
    
    # Confusion matrix
    cm = confusion_matrix(df['label_true'], predictions)
    print("\nConfusion Matrix:")
    print(f"                  Predicted Non-SDL  Predicted SDL")
    print(f"  Actual Non-SDL:  {cm[0,0]:>15,}  {cm[0,1]:>13,}")
    print(f"  Actual SDL:      {cm[1,0]:>15,}  {cm[1,1]:>13,}")
    
    # Calculate metrics
    tn, fp, fn, tp = cm.ravel()
    
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0  # Positive Predictive Value
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0  # Negative Predictive Value
    
    print(f"\nDiagnostic Statistics:")
    print(f"  Sensitivity (Recall):     {sensitivity:.4f}")
    print(f"  Specificity:              {specificity:.4f}")
    print(f"  Positive Predictive Value (Precision): {ppv:.4f}")
    print(f"  Negative Predictive Value: {npv:.4f}")
    
    # New SDL discoveries
    new_sdl = df[(predictions == 1) & (df['label_true'] == 0)]
    print(f"\nNew SDL Discoveries (above threshold):")
    print(f"  Count: {len(new_sdl):,}")
    
    if len(new_sdl) > 0:
        print(f"  By field:")
        for field in sorted(new_sdl['field'].unique()):
            count = (new_sdl['field'] == field).sum()
            pct = count / len(new_sdl) * 100
            print(f"    {field}: {count:,} ({pct:.1f}%)")

# ==============================================================================
# 3. PRECISION-RECALL CURVE
# ==============================================================================

print("\n" + "="*70)
print("3. PRECISION-RECALL ANALYSIS")
print("="*70)

precision_vals, recall_vals, pr_thresholds = precision_recall_curve(
    df['label_true'], 
    df[score_col]
)

# Find optimal threshold (max F1)
f1_scores = 2 * (precision_vals * recall_vals) / (precision_vals + recall_vals + 1e-10)
optimal_idx = np.argmax(f1_scores[:-1])  # Exclude last element
optimal_threshold = pr_thresholds[optimal_idx]

print(f"\nOptimal Threshold (Max F1): {optimal_threshold:.4f}")
print(f"  Precision: {precision_vals[optimal_idx]:.4f}")
print(f"  Recall: {recall_vals[optimal_idx]:.4f}")
print(f"  F1 Score: {f1_scores[optimal_idx]:.4f}")

# Save PR curve data
pr_df = pd.DataFrame({
    'threshold': list(pr_thresholds) + [1.0],
    'precision': precision_vals,
    'recall': recall_vals,
    'f1': list(f1_scores)
})
pr_df.to_csv(f"{OUTPUT_DIR}/precision_recall_curve.csv", index=False)
print(f"\n✓ Saved PR curve data to: {OUTPUT_DIR}/precision_recall_curve.csv")

# ==============================================================================
# 4. ROC CURVE ANALYSIS
# ==============================================================================

print("\n" + "="*70)
print("4. ROC CURVE ANALYSIS")
print("="*70)

fpr, tpr, roc_thresholds = roc_curve(df['label_true'], df[score_col])
roc_auc = auc(fpr, tpr)

print(f"\nROC AUC Score: {roc_auc:.4f}")

# Find threshold for 95% TPR (recall)
idx_95_tpr = np.argmax(tpr >= 0.95)
thresh_95_tpr = roc_thresholds[idx_95_tpr]
fpr_at_95_tpr = fpr[idx_95_tpr]

print(f"\nAt 95% Recall:")
print(f"  Threshold: {thresh_95_tpr:.4f}")
print(f"  False Positive Rate: {fpr_at_95_tpr:.4f}")
print(f"  False Positives: {int(fpr_at_95_tpr * (df['label_true'] == 0).sum()):,}")

# Save ROC data
roc_df = pd.DataFrame({
    'fpr': fpr,
    'tpr': tpr,
    'threshold': list(roc_thresholds) + [roc_thresholds[-1]]
})
roc_df.to_csv(f"{OUTPUT_DIR}/roc_curve.csv", index=False)
print(f"\n✓ Saved ROC curve data to: {OUTPUT_DIR}/roc_curve.csv")

# ==============================================================================
# 5. SCORE DISTRIBUTION ANALYSIS
# ==============================================================================

print("\n" + "="*70)
print("5. SCORE DISTRIBUTION ANALYSIS")
print("="*70)

known_sdl = df[df['label_true'] == 1][score_col]
background = df[df['label_true'] == 0][score_col]

print(f"\nKnown SDL Papers:")
print(f"  Count: {len(known_sdl):,}")
print(f"  Mean: {known_sdl.mean():.4f}")
print(f"  Median: {known_sdl.median():.4f}")
print(f"  Std: {known_sdl.std():.4f}")
print(f"  Min: {known_sdl.min():.4f}")
print(f"  Max: {known_sdl.max():.4f}")

print(f"\nBackground Papers:")
print(f"  Count: {len(background):,}")
print(f"  Mean: {background.mean():.4f}")
print(f"  Median: {background.median():.4f}")
print(f"  Std: {background.std():.4f}")
print(f"  Min: {background.min():.4f}")
print(f"  Max: {background.max():.4f}")

print(f"\nSeparation Metrics:")
print(f"  Mean Difference: {known_sdl.mean() - background.mean():.4f}")
print(f"  Cohen's D: {(known_sdl.mean() - background.mean()) / np.sqrt((known_sdl.std()**2 + background.std()**2) / 2):.4f}")

# ==============================================================================
# 6. FIELD-SPECIFIC ANALYSIS
# ==============================================================================

print("\n" + "="*70)
print("6. FIELD-SPECIFIC PERFORMANCE")
print("="*70)

for field in sorted(df['field'].unique()):
    field_df = df[df['field'] == field]
    field_sdl = field_df[field_df['label_true'] == 1]
    
    print(f"\n{field}:")
    print(f"  Total papers: {len(field_df):,}")
    print(f"  Known SDL: {len(field_sdl):,}")
    
    if len(field_sdl) > 0:
        print(f"  SDL mean score: {field_sdl[score_col].mean():.4f}")
        print(f"  SDL recall @0.9: {(field_sdl[score_col] >= 0.9).sum() / len(field_sdl) * 100:.1f}%")
    
    # High scorers in this field
    high_scorers = field_df[field_df[score_col] > 0.9]
    new_finds = high_scorers[high_scorers['label_true'] == 0]
    print(f"  Papers >0.9: {len(high_scorers):,}")
    print(f"  New SDL candidates: {len(new_finds):,}")

# ==============================================================================
# 7. RECOMMENDATIONS SUMMARY
# ==============================================================================

print("\n" + "="*70)
print("7. RECOMMENDATIONS BASED ON ANALYSIS")
print("="*70)

# Analyze trade-offs
print(f"\nThreshold Recommendations:")

# Conservative (high precision)
conservative_thresh = 0.95
conservative_pred = (df[score_col] >= conservative_thresh).astype(int)
tn, fp, fn, tp = confusion_matrix(df['label_true'], conservative_pred).ravel()
conservative_precision = tp / (tp + fp) if (tp + fp) > 0 else 0
conservative_recall = tp / (tp + fn) if (tp + fn) > 0 else 0

print(f"\n  CONSERVATIVE (Threshold = {conservative_thresh}):")
print(f"    Use when: You want high confidence in SDL identification")
print(f"    Precision: {conservative_precision:.4f} (Low false positives)")
print(f"    Recall: {conservative_recall:.4f}")
print(f"    Predicted SDLs: {conservative_pred.sum():,}")
print(f"    Trade-off: Miss {fn:,} known SDLs")

# Balanced (max F1)
balanced_thresh = optimal_threshold
balanced_pred = (df[score_col] >= balanced_thresh).astype(int)
tn, fp, fn, tp = confusion_matrix(df['label_true'], balanced_pred).ravel()
balanced_precision = tp / (tp + fp) if (tp + fp) > 0 else 0
balanced_recall = tp / (tp + fn) if (tp + fn) > 0 else 0

print(f"\n  BALANCED (Threshold = {balanced_thresh:.4f}):")
print(f"    Use when: You want best overall performance")
print(f"    Precision: {balanced_precision:.4f}")
print(f"    Recall: {balanced_recall:.4f}")
print(f"    Predicted SDLs: {balanced_pred.sum():,}")

# Liberal (high recall)
liberal_thresh = 0.7
liberal_pred = (df[score_col] >= liberal_thresh).astype(int)
tn, fp, fn, tp = confusion_matrix(df['label_true'], liberal_pred).ravel()
liberal_precision = tp / (tp + fp) if (tp + fp) > 0 else 0
liberal_recall = tp / (tp + fn) if (tp + fn) > 0 else 0

print(f"\n  LIBERAL (Threshold = {liberal_thresh}):")
print(f"    Use when: You want to catch all possible SDLs")
print(f"    Precision: {liberal_precision:.4f}")
print(f"    Recall: {liberal_recall:.4f} (Catch most SDLs)")
print(f"    Predicted SDLs: {liberal_pred.sum():,}")
print(f"    Trade-off: {fp:,} false positives to review")

# ==============================================================================
# 8. SAVE COMPREHENSIVE SUMMARY
# ==============================================================================

print("\n" + "="*70)
print("8. SAVING COMPREHENSIVE SUMMARY")
print("="*70)

summary = {
    'Total Papers': len(df),
    'Known SDL': int((df['label_true'] == 1).sum()),
    'Background': int((df['label_true'] == 0).sum()),
    '': '',
    'Score Statistics': '',
    'Mean Score (All)': f"{df[score_col].mean():.4f}",
    'Mean Score (SDL)': f"{known_sdl.mean():.4f}",
    'Mean Score (Background)': f"{background.mean():.4f}",
    'Std Dev (All)': f"{df[score_col].std():.4f}",
    ' ': '',
    'ROC AUC': f"{roc_auc:.4f}",
    '  ': '',
    'Optimal Threshold (Max F1)': f"{optimal_threshold:.4f}",
    'Optimal F1 Score': f"{f1_scores[optimal_idx]:.4f}",
    'Optimal Precision': f"{precision_vals[optimal_idx]:.4f}",
    'Optimal Recall': f"{recall_vals[optimal_idx]:.4f}",
    '   ': '',
    'Conservative (0.95)': '',
    'Conservative Precision': f"{conservative_precision:.4f}",
    'Conservative Recall': f"{conservative_recall:.4f}",
    'Conservative Predicted': int(conservative_pred.sum()),
    '    ': '',
    'Balanced (Optimal)': '',
    'Balanced Precision': f"{balanced_precision:.4f}",
    'Balanced Recall': f"{balanced_recall:.4f}",
    'Balanced Predicted': int(balanced_pred.sum()),
    '     ': '',
    'Liberal (0.70)': '',
    'Liberal Precision': f"{liberal_precision:.4f}",
    'Liberal Recall': f"{liberal_recall:.4f}",
    'Liberal Predicted': int(liberal_pred.sum())
}

summary_df = pd.DataFrame([summary]).T
summary_df.columns = ['Value']
summary_df.to_csv(f"{OUTPUT_DIR}/comprehensive_summary.csv")

print(f"\n✓ Saved comprehensive summary to: {OUTPUT_DIR}/comprehensive_summary.csv")

print("\n" + "="*70)
print("ANALYSIS COMPLETE")
print("="*70)
print(f"\nGenerated Files:")
print(f"  1. {OUTPUT_DIR}/threshold_analysis.csv")
print(f"  2. {OUTPUT_DIR}/precision_recall_curve.csv")
print(f"  3. {OUTPUT_DIR}/roc_curve.csv")
print(f"  4. {OUTPUT_DIR}/comprehensive_summary.csv")
print("="*70 + "\n")