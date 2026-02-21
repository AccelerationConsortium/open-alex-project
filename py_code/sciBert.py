
## TRAINING ITERATION 1
import pandas as pd
import numpy as np
import torch
import os
from sklearn.model_selection import train_test_split
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
# EXACT paths based on your EDA report
INPUT_FILE = "/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_subset.csv"
OUTPUT_DIR = "/project/def-kmcel/hridansh/openalex_project/data/scibert"
RESULTS_FILE = "/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_scibert_scores.csv"

# Hyperparameters
MODEL_NAME = "/project/def-kmcel/hridansh/openalex_project/data/scibert"
MAX_LENGTH = 512
BATCH_SIZE = 16   # Optimized for standard Narval GPU memory
EPOCHS = 4
LEARNING_RATE = 2e-5

def load_and_prep_data():
    print(f"Loading data from {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE, low_memory=False)
    
    # Fill NAs to prevent errors
    df['abstract'] = df['abstract'].fillna("")
    df['title'] = df['title'].fillna("")
    
    # Combine Title + Abstract (The [SEP] token helps BERT distinguish them)
    df['text'] = df['title'] + " [SEP] " + df['abstract']
    
    # CREATE TRUTH LABELS
    # Label = 1 if it is in Manual List OR Keyword List
    df['label'] = ((df['SDL'] == 1) | (df['SDL_Keyword_Paper'] == 1)).astype(int)
    
    return df

def create_balanced_training_set(df):
    print("Creating balanced training set...")
    
    # 1. POSITIVES: All known SDL papers
    positives = df[df['label'] == 1]
    
    # 2. NEGATIVES: Chemistry/MatSci only (No Engineering to avoid Robotics/Lidar)
    negatives = df[
        (df['label'] == 0) & 
        (df['field'].isin(['chemistry', 'materials_science']))
    ]
    
    # 3. BALANCE: Downsample negatives to match positives 1:1
    n_pos = len(positives)
    # Safety check if we have enough negatives
    n_neg = min(len(negatives), n_pos)
    
    negatives_downsampled = negatives.sample(n=n_neg, random_state=42)
    
    print(f"Training Counts -> Positives: {len(positives)}, Negatives: {len(negatives_downsampled)}")
    
    # Combine and Shuffle
    train_df = pd.concat([positives, negatives_downsampled]).sample(frac=1, random_state=42).reset_index(drop=True)
    return train_df

def tokenize_function(examples, tokenizer):
    return tokenizer(
        examples["text"], 
        truncation=True, 
        padding="max_length", 
        max_length=MAX_LENGTH
    )

def main():
    # Setup Output Directory
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # --- STEP 1: PREPARE DATA ---
    full_df = load_and_prep_data()
    train_df = create_balanced_training_set(full_df)
    
    # --- STEP 2: SETUP MODEL ---
    print(f"Loading SciBERT model: {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, 
        num_labels=2
    )
    
    # --- STEP 3: DATASET CONVERSION ---
    hf_train = Dataset.from_pandas(train_df[['text', 'label']])
    
    # Split 80/20 Train/Val
    split_dataset = hf_train.train_test_split(test_size=0.2)
    
    # Tokenize
    tokenized_datasets = split_dataset.map(lambda x: tokenize_function(x, tokenizer), batched=True)
    
    # --- STEP 4: TRAINING ---
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        num_train_epochs=EPOCHS,
        weight_decay=0.01,
        load_best_model_at_end=True,
        save_total_limit=2,
        logging_dir=f"{OUTPUT_DIR}/logs",
        fp16=True, # Use mixed precision for speed on GPUs
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
    )
    
    print("Starting training...")
    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)  # <--- ADD THIS LINE
    print("Training complete.")
    
    # --- STEP 5: INFERENCE ON FULL DATASET ---
    print(f"Running inference on full dataset ({len(full_df)} papers)...")
    
    full_hf_dataset = Dataset.from_pandas(full_df[['text']])
    tokenized_full = full_hf_dataset.map(lambda x: tokenize_function(x, tokenizer), batched=True)
    
    # Run prediction
    predictions = trainer.predict(tokenized_full)
    
    # Convert logits to probabilities (Softmax)
    probs = torch.nn.functional.softmax(torch.tensor(predictions.predictions), dim=-1)
    
    # We want the probability of Class 1 (SDL)
    # The output is [Prob_0, Prob_1]
    sdl_probs = probs[:, 1].numpy()
    
    # --- STEP 6: SAVE RESULTS ---
    # We create a lightweight CSV with just IDs and Scores
    output_df = full_df[['article_id', 'doi', 'title', 'SDL', 'SDL_Keyword_Paper', 'field']].copy()
    output_df['scibert_sdl_prob'] = sdl_probs
    
    output_df.to_csv(RESULTS_FILE, index=False)
    print(f"DONE. Scores saved to: {RESULTS_FILE}")

if __name__ == "__main__":
    main()

## TRAINING ITERATION 2 & 3
# import pandas as pd
# import numpy as np
# import torch
# import os
# from sklearn.model_selection import train_test_split
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

# # 1. TRAINING DATA (The small, clean V2 file)
# TRAIN_FILE = "/project/def-kmcel/hridansh/openalex_project/data/scibert/training_data_v3.csv"

# # 2. INFERENCE DATA (The original big dataset to be scored)
# # Note: Use the path to your main 490k file here
# INFERENCE_FILE = "/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_subset.csv"

# # 3. OUTPUTS
# OUTPUT_DIR = "/project/def-kmcel/hridansh/openalex_project/data/scibert"
# RESULTS_FILE = "/project/def-kmcel/hridansh/openalex_project/data/scibert/iteration_3_scibert_scores.csv"

# # 4. MODEL (Local Path)
# MODEL_PATH = "/project/def-kmcel/hridansh/openalex_project/data/scibert/training/iteration_2"

# # Hyperparameters
# MAX_LENGTH = 512
# BATCH_SIZE = 16
# EPOCHS = 4
# LEARNING_RATE = 2e-5

# def tokenize_function(examples, tokenizer):
#     return tokenizer(
#         examples["text"], 
#         truncation=True, 
#         padding="max_length", 
#         max_length=MAX_LENGTH
#     )

# def main():
#     # --- SETUP ---
#     if not os.path.exists(OUTPUT_DIR):
#         os.makedirs(OUTPUT_DIR)

#     print(f"Loading Tokenizer/Model from: {MODEL_PATH}")
#     tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
#     model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, num_labels=2)

#     # ==========================================================================
#     # PART 1: TRAINING (Using V2 Clean Data)
#     # ==========================================================================
#     print(f"\n--- LOADING TRAINING DATA: {TRAIN_FILE} ---")
#     # This file ALREADY has 'text' and 'label' columns. No prep needed.
#     train_df = pd.read_csv(TRAIN_FILE)
#     print(f"Training Rows: {len(train_df)}")
#     print(f"Labels: {train_df['label'].value_counts().to_dict()}")

#     # Convert to Hugging Face Dataset
#     hf_train = Dataset.from_pandas(train_df[['text', 'label']])
    
#     # Split
#     split_dataset = hf_train.train_test_split(test_size=0.1) # 10% validation is enough for small clean data
    
#     # Tokenize
#     print("Tokenizing training data...")
#     tokenized_datasets = split_dataset.map(lambda x: tokenize_function(x, tokenizer), batched=True)

#     # Train
#     training_args = TrainingArguments(
#         output_dir=OUTPUT_DIR,
#         eval_strategy="epoch",
#         save_strategy="epoch",
#         learning_rate=LEARNING_RATE,
#         per_device_train_batch_size=BATCH_SIZE,
#         per_device_eval_batch_size=BATCH_SIZE,
#         num_train_epochs=EPOCHS,
#         weight_decay=0.01,
#         load_best_model_at_end=True,
#         save_total_limit=2,
#         logging_dir=f"{OUTPUT_DIR}/logs",
#         fp16=True, 
#     )
    
#     trainer = Trainer(
#         model=model,
#         args=training_args,
#         train_dataset=tokenized_datasets["train"],
#         eval_dataset=tokenized_datasets["test"],
#         data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
#     )
    
#     print("Starting training...")
#     trainer.train()
    
#     # Save Model & Tokenizer
#     trainer.save_model(OUTPUT_DIR)
#     tokenizer.save_pretrained(OUTPUT_DIR)
#     print("Training complete. Model saved.")

#     # ==========================================================================
#     # PART 2: INFERENCE (Using Original Big Data)
#     # ==========================================================================
#     print(f"\n--- LOADING INFERENCE DATA: {INFERENCE_FILE} ---")
#     full_df = pd.read_csv(INFERENCE_FILE, low_memory=False)
    
#     # We must prep this data because it is RAW (separate title/abstract)
#     print("Prepping inference text (combining Title + Abstract)...")
#     full_df['abstract'] = full_df['abstract'].fillna("")
#     full_df['title'] = full_df['title'].fillna("")
#     full_df['text'] = full_df['title'] + " [SEP] " + full_df['abstract']
    
#     print(f"Scoring {len(full_df)} papers...")
#     full_hf_dataset = Dataset.from_pandas(full_df[['text']])
#     tokenized_full = full_hf_dataset.map(lambda x: tokenize_function(x, tokenizer), batched=True)
    
#     # Predict
#     predictions = trainer.predict(tokenized_full)
#     probs = torch.nn.functional.softmax(torch.tensor(predictions.predictions), dim=-1)
#     sdl_probs = probs[:, 1].numpy()
    
#     # Export Results
#     # Keep key columns + new score
#     output_cols = ['article_id', 'doi', 'title', 'SDL', 'SDL_Keyword_Paper', 'field']
#     # Check if cols exist (to be safe)
#     valid_cols = [c for c in output_cols if c in full_df.columns]
    
#     output_df = full_df[valid_cols].copy()
#     output_df['scibert_sdl_prob'] = sdl_probs
    
#     output_df.to_csv(RESULTS_FILE, index=False)
#     print(f"DONE. Scores saved to: {RESULTS_FILE}")

# if __name__ == "__main__":
#     main()

# # ANALYSIS OF SCIBERT (ITERATION 1)
# import pandas as pd
# import numpy as np
# from sklearn.feature_extraction.text import CountVectorizer
# import os

# # ==============================================================================
# # CONFIGURATION
# # ==============================================================================
# # 1. The File with the SCORES (Generated by SciBERT)
# SCORES_FILE = "/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_scibert_scores.csv"

# # 2. The File with the TEXT (Your original dataset)
# ORIGINAL_DATA_FILE = "1regression/test/regression_dataset_subset.csv"

# OUTPUT_DIR = "/project/def-kmcel/hridansh/openalex_project/data/analysis_deep"
# os.makedirs(OUTPUT_DIR, exist_ok=True)

# # ==============================================================================
# # 1. LOAD AND MERGE
# # ==============================================================================
# print(f"Loading scores from {SCORES_FILE}...")
# df_scores = pd.read_csv(SCORES_FILE)

# print(f"Loading original text from {ORIGINAL_DATA_FILE}...")
# # We only need ID and Abstract to merge
# df_text = pd.read_csv(ORIGINAL_DATA_FILE, usecols=['article_id', 'abstract', 'title', 'SDL', 'SDL_Keyword_Paper'])

# print("Merging datasets...")
# # Merge on article_id to get the text back
# df = pd.merge(df_scores, df_text, on='article_id', suffixes=('', '_orig'))

# # Handle duplicate columns if any exist after merge
# if 'SDL_orig' in df.columns:
#     df['SDL'] = df['SDL_orig']
# if 'SDL_Keyword_Paper_orig' in df.columns:
#     df['SDL_Keyword_Paper'] = df['SDL_Keyword_Paper_orig']
    
# # Fill NA text
# df['title'] = df['title'].fillna("")
# df['abstract'] = df['abstract'].fillna("")
# df['full_text'] = df['title'] + " " + df['abstract']

# # Define "Ground Truth" (Union of Manual + Keyword)
# df['Is_Known_SDL'] = ((df['SDL'] == 1) | (df['SDL_Keyword_Paper'] == 1)).astype(int)

# print(f"Merged Data Shape: {df.shape}")

# # ==============================================================================
# # 2. SCORE DISTRIBUTION ANALYSIS
# # ==============================================================================
# print("\n=== 1. SCORE DISTRIBUTION ===")
# known_sdl_scores = df[df['Is_Known_SDL'] == 1]['scibert_sdl_prob']
# random_scores = df[df['Is_Known_SDL'] == 0]['scibert_sdl_prob']

# print(f"Known SDLs (n={len(known_sdl_scores)}):")
# print(f"  Mean Score: {known_sdl_scores.mean():.4f}")
# print(f"  Median Score: {known_sdl_scores.median():.4f}")
# print(f"  > 0.90: {(known_sdl_scores > 0.9).sum()} ({((known_sdl_scores > 0.9).sum()/len(known_sdl_scores))*100:.1f}%)")
# print(f"  < 0.10 (Missed): {(known_sdl_scores < 0.1).sum()} ({((known_sdl_scores < 0.1).sum()/len(known_sdl_scores))*100:.1f}%)")

# print(f"\nBackground Papers (n={len(random_scores)}):")
# print(f"  Mean Score: {random_scores.mean():.4f}")
# print(f"  > 0.90 (Potential New Finds): {(random_scores > 0.9).sum()}")

# # ==============================================================================
# # 3. LEXICAL DIVERGENCE (Log-Odds Ratio)
# # ==============================================================================
# print("\n=== 2. DISTINCTIVE VOCABULARY (Log-Odds) ===")

# # High Confidence SDL (>0.90) vs Low Confidence (<0.10)
# high_conf_idx = df['scibert_sdl_prob'] > 0.90
# low_conf_idx = df['scibert_sdl_prob'] < 0.10

# if high_conf_idx.sum() < 10:
#     print("Not enough high-confidence papers for lexical analysis.")
# else:
#     print("Extracting distinctive phrases...")
#     vec = CountVectorizer(ngram_range=(2, 3), stop_words='english', min_df=5, max_features=50000)
    
#     # Create subset for analysis
#     subset_df = pd.concat([df[high_conf_idx], df[low_conf_idx]])
#     y = np.where(subset_df['scibert_sdl_prob'] > 0.90, 1, 0)
    
#     X = vec.fit_transform(subset_df['full_text'])
    
#     # Counts + Smoothing
#     X_pos = X[y == 1]
#     X_neg = X[y == 0]
#     pos_counts = np.array(X_pos.sum(axis=0)).flatten() + 1
#     neg_counts = np.array(X_neg.sum(axis=0)).flatten() + 1
    
#     # Log Odds
#     pos_norm = pos_counts / pos_counts.sum()
#     neg_norm = neg_counts / neg_counts.sum()
#     log_odds = np.log(pos_norm / neg_norm)
    
#     vocab = {v: k for k, v in vec.vocabulary_.items()}
    
#     # Top SDL Words
#     print("\nTop 30 Phrases Driving High Scores (The 'Signal'):")
#     for idx in log_odds.argsort()[::-1][:30]:
#         print(f"  + {vocab[idx]} (Score: {log_odds[idx]:.2f})")
        
#     # Top Non-SDL Words
#     print("\nTop 20 Phrases Driving Low Scores (The 'Noise'):")
#     for idx in log_odds.argsort()[:20]:
#         print(f"  - {vocab[idx]} (Score: {log_odds[idx]:.2f})")

# # ==============================================================================
# # 4. TOPIC CONFOUNDING CHECK
# # ==============================================================================
# print("\n=== 3. TOPIC BIAS CHECK ===")
# confounders = ['perovskite', 'battery', 'solar cell', 'drug discovery', 'catalysis']
# print(f"{'Keyword':<20} | {'Avg Score':<10} | {'Count':<10}")
# print("-" * 45)
# for word in confounders:
#     mask = df['full_text'].str.lower().str.contains(word)
#     avg_score = df[mask]['scibert_sdl_prob'].mean()
#     count = mask.sum()
#     print(f"{word:<20} | {avg_score:.4f}     | {count:<10}")

# # ==============================================================================
# # 5. EXPORTS
# # ==============================================================================
# print("\n=== 4. EXPORTING FILES ===")

# # Confused Papers (0.4 - 0.6)
# confused_path = f"{OUTPUT_DIR}/confused_papers_active_learning.csv"
# df[(df['scibert_sdl_prob'] > 0.40) & (df['scibert_sdl_prob'] < 0.60)][
#     ['doi', 'title', 'abstract', 'scibert_sdl_prob']
# ].head(50).to_csv(confused_path, index=False)
# print(f"Saved 'Confused' papers to: {confused_path}")

# # New High Confidence
# hall_path = f"{OUTPUT_DIR}/high_confidence_new_finds.csv"
# df[(df['scibert_sdl_prob'] > 0.95) & (df['Is_Known_SDL'] == 0)][
#     ['doi', 'title', 'abstract', 'scibert_sdl_prob']
# ].head(50).to_csv(hall_path, index=False)
# print(f"Saved 'High Confidence New' papers to: {hall_path}")

# # Hard Misses
# missed_path = f"{OUTPUT_DIR}/hard_false_negatives.csv"
# df[(df['scibert_sdl_prob'] < 0.20) & (df['Is_Known_SDL'] == 1)][
#     ['doi', 'title', 'abstract', 'scibert_sdl_prob', 'SDL', 'SDL_Keyword_Paper']
# ].to_csv(missed_path, index=False)
# print(f"Saved 'Hard Missed' papers to: {missed_path}")

# print("\nDone.")


# # ANALYSIS OF SCIBERT (ITERATION 2)
# import pandas as pd
# import numpy as np
# from sklearn.feature_extraction.text import CountVectorizer
# import os

# # ==============================================================================
# # CONFIGURATION
# # ==============================================================================
# # 1. The NEW Scores File (v2)
# SCORES_FILE = "/project/def-kmcel/hridansh/openalex_project/data/scibert/iteration_2_scibert_scores.csv"

# # 2. The Original Text File (v21)
# ORIGINAL_DATA_FILE = "/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_subset.csv"

# OUTPUT_DIR = "/project/def-kmcel/hridansh/openalex_project/data/scibert"
# os.makedirs(OUTPUT_DIR, exist_ok=True)

# # ==============================================================================
# # 1. LOAD AND MERGE
# # ==============================================================================
# print(f"Loading NEW scores from {SCORES_FILE}...")
# if not os.path.exists(SCORES_FILE):
#     print(f"ERROR: Could not find {SCORES_FILE}. Did the training job finish?")
#     exit()

# df_scores = pd.read_csv(SCORES_FILE)

# print(f"Loading original text from {ORIGINAL_DATA_FILE}...")
# # We only need ID and Abstract to merge
# df_text = pd.read_csv(ORIGINAL_DATA_FILE, usecols=['article_id', 'abstract', 'title', 'SDL', 'SDL_Keyword_Paper'])

# print("Merging datasets...")
# # Merge on article_id to get the text back
# df = pd.merge(df_scores, df_text, on='article_id', suffixes=('', '_orig'))

# # Handle duplicate columns if any exist after merge
# if 'SDL_orig' in df.columns:
#     df['SDL'] = df['SDL_orig']
# if 'SDL_Keyword_Paper_orig' in df.columns:
#     df['SDL_Keyword_Paper'] = df['SDL_Keyword_Paper_orig']
    
# # Fill NA text
# df['title'] = df['title'].fillna("")
# df['abstract'] = df['abstract'].fillna("")
# df['full_text'] = df['title'] + " " + df['abstract']

# # Define "Ground Truth" (Union of Manual + Keyword)
# df['Is_Known_SDL'] = ((df['SDL'] == 1) | (df['SDL_Keyword_Paper'] == 1)).astype(int)

# print(f"Merged Data Shape: {df.shape}")

# # ==============================================================================
# # 2. SCORE DISTRIBUTION ANALYSIS
# # ==============================================================================
# print("\n=== 1. SCORE DISTRIBUTION (v2) ===")
# known_sdl_scores = df[df['Is_Known_SDL'] == 1]['scibert_sdl_prob']
# random_scores = df[df['Is_Known_SDL'] == 0]['scibert_sdl_prob']

# print(f"Known SDLs (n={len(known_sdl_scores)}):")
# print(f"  Mean Score: {known_sdl_scores.mean():.4f}")
# print(f"  Median Score: {known_sdl_scores.median():.4f}")
# print(f"  > 0.90: {(known_sdl_scores > 0.9).sum()} ({((known_sdl_scores > 0.9).sum()/len(known_sdl_scores))*100:.1f}%)")
# print(f"  < 0.10 (Missed): {(known_sdl_scores < 0.1).sum()} ({((known_sdl_scores < 0.1).sum()/len(known_sdl_scores))*100:.1f}%)")

# print(f"\nBackground Papers (n={len(random_scores)}):")
# print(f"  Mean Score: {random_scores.mean():.4f}")
# print(f"  > 0.90 (Potential New Finds): {(random_scores > 0.9).sum()}")
# print(f"  (Previous v1 count was ~141,000. We want this lower!)")

# # ==============================================================================
# # 3. LEXICAL DIVERGENCE (Log-Odds Ratio)
# # ==============================================================================
# print("\n=== 2. DISTINCTIVE VOCABULARY (Log-Odds) ===")

# # High Confidence SDL (>0.90) vs Low Confidence (<0.10)
# high_conf_idx = df['scibert_sdl_prob'] > 0.90
# low_conf_idx = df['scibert_sdl_prob'] < 0.10

# if high_conf_idx.sum() < 10:
#     print("Not enough high-confidence papers for lexical analysis.")
# else:
#     print("Extracting distinctive phrases...")
#     vec = CountVectorizer(ngram_range=(2, 3), stop_words='english', min_df=5, max_features=50000)
    
#     # Create subset for analysis
#     subset_df = pd.concat([df[high_conf_idx], df[low_conf_idx]])
#     y = np.where(subset_df['scibert_sdl_prob'] > 0.90, 1, 0)
    
#     X = vec.fit_transform(subset_df['full_text'])
    
#     # Counts + Smoothing
#     X_pos = X[y == 1]
#     X_neg = X[y == 0]
#     pos_counts = np.array(X_pos.sum(axis=0)).flatten() + 1
#     neg_counts = np.array(X_neg.sum(axis=0)).flatten() + 1
    
#     # Log Odds
#     pos_norm = pos_counts / pos_counts.sum()
#     neg_norm = neg_counts / neg_counts.sum()
#     log_odds = np.log(pos_norm / neg_norm)
    
#     vocab = {v: k for k, v in vec.vocabulary_.items()}
    
#     # Top SDL Words
#     print("\nTop 30 Phrases Driving High Scores (The 'Signal'):")
#     print("(Check if 'Adversarial' is gone and 'Liquid Handler' is back)")
#     for idx in log_odds.argsort()[::-1][:30]:
#         print(f"  + {vocab[idx]} (Score: {log_odds[idx]:.2f})")
        
#     # Top Non-SDL Words
#     print("\nTop 20 Phrases Driving Low Scores (The 'Noise'):")
#     print("(Check if 'Altmetric' is gone)")
#     for idx in log_odds.argsort()[:20]:
#         print(f"  - {vocab[idx]} (Score: {log_odds[idx]:.2f})")

# # ==============================================================================
# # 4. TOPIC CONFOUNDING CHECK
# # ==============================================================================
# print("\n=== 3. TOPIC BIAS CHECK ===")
# confounders = ['perovskite', 'battery', 'solar cell', 'drug discovery', 'catalysis', 'simulation', 'density functional']
# print(f"{'Keyword':<20} | {'Avg Score':<10} | {'Count':<10}")
# print("-" * 45)
# for word in confounders:
#     mask = df['full_text'].str.lower().str.contains(word)
#     avg_score = df[mask]['scibert_sdl_prob'].mean()
#     count = mask.sum()
#     print(f"{word:<20} | {avg_score:.4f}     | {count:<10}")

# # ==============================================================================
# # 5. EXPORTS
# # ==============================================================================
# print("\n=== 4. EXPORTING FILES ===")

# # Confused Papers (0.4 - 0.6)
# confused_path = f"{OUTPUT_DIR}/confused_papers_active_learning.csv"
# df[(df['scibert_sdl_prob'] > 0.40) & (df['scibert_sdl_prob'] < 0.60)][
#     ['doi', 'title', 'abstract', 'scibert_sdl_prob']
# ].head(50).to_csv(confused_path, index=False)
# print(f"Saved 'Confused' papers to: {confused_path}")

# # New High Confidence
# hall_path = f"{OUTPUT_DIR}/high_confidence_new_finds.csv"
# df[(df['scibert_sdl_prob'] > 0.95) & (df['Is_Known_SDL'] == 0)][
#     ['doi', 'title', 'abstract', 'scibert_sdl_prob']
# ].head(50).to_csv(hall_path, index=False)
# print(f"Saved 'High Confidence New' papers to: {hall_path}")

# # Hard Misses
# missed_path = f"{OUTPUT_DIR}/hard_false_negatives.csv"
# df[(df['scibert_sdl_prob'] < 0.20) & (df['Is_Known_SDL'] == 1)][
#     ['doi', 'title', 'abstract', 'scibert_sdl_prob', 'SDL', 'SDL_Keyword_Paper']
# ].to_csv(missed_path, index=False)
# print(f"Saved 'Hard Missed' papers to: {missed_path}")

# print("\nDone.")

# ### CREATING SPECIFIC DATASET (ITERATION 2)
# import pandas as pd
# import numpy as np
# import re

# # ==============================================================================
# # CONFIGURATION
# # ==============================================================================
# INPUT_FILE = "/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_subset.csv"
# OUTPUT_FILE = "/project/def-kmcel/hridansh/openalex_project/data/scibert/training_data_v2_cleaned.csv"

# # ==============================================================================
# # 1. TEXT CLEANING FUNCTION (Removing the "Cheating" Signals)
# # ==============================================================================
# def clean_abstract(text):
#     if pd.isna(text) or text == "":
#         return ""
    
#     text = str(text)
    
#     # 1. Remove "Altmetric" and "Article Views" blocks (Common in your False Negatives)
#     text = re.sub(r'Article Views\s*\d+', '', text, flags=re.IGNORECASE)
#     text = re.sub(r'Altmetric\s*-?\s*Citations\s*\d*', '', text, flags=re.IGNORECASE)
#     text = re.sub(r'Altmetric Attention Score', '', text, flags=re.IGNORECASE)
#     text = re.sub(r'LEARN ABOUT THESE METRICS', '', text, flags=re.IGNORECASE)
    
#     # 2. Remove Copyrights
#     text = re.sub(r'©\s*\d{4}\s*.*', '', text)  # © 2013 American Chemical Society
#     text = re.sub(r'Copyright\s*©\s*\d{4}.*', '', text, flags=re.IGNORECASE)
    
#     # 3. Remove URLs and DOIs (Model memorizes these as "Journal X patterns")
#     text = re.sub(r'https?://\S+', '', text)
#     text = re.sub(r'doi:\s*10\.\S+', '', text, flags=re.IGNORECASE)
    
#     # 4. Remove "Funding" or "Acknowledgement" tails (often biases towards certain grants)
#     text = re.sub(r'Funding\s*Information:.*', '', text, flags=re.IGNORECASE)
    
#     return text.strip()

# # ==============================================================================
# # 2. BUILD THE DATASET
# # ==============================================================================
# print(f"Loading {INPUT_FILE}...")
# df = pd.read_csv(INPUT_FILE, low_memory=False)

# # A. Apply Cleaning
# print("Cleaning abstracts (removing footers/metadata)...")
# df['abstract_clean'] = df['abstract'].apply(clean_abstract)
# df['text'] = df['title'].fillna("") + " [SEP] " + df['abstract_clean']

# # B. Define Positives (The "Truth")
# # Same as before: Manual List + Keyword List
# positives = df[(df['SDL'] == 1) | (df['SDL_Keyword_Paper'] == 1)].copy()
# positives['label'] = 1

# # C. Define Negatives (The "Hard" Part)
# # We need a mix of "Random" and "Hard" negatives.

# # C1. Hard Negatives: Computational/Simulation papers that are NOT SDLs
# # These teach the model: "Computers != Robots"
# hard_neg_keywords = ['dft', 'density functional theory', 'molecular dynamics', 
#                      'simulation', 'computational study', 'theoretical', 
#                      'in silico', 'vasp', 'gaussian', 'neural network']
# pattern = '|'.join(hard_neg_keywords)

# hard_negatives = df[
#     (df['SDL'] == 0) & 
#     (df['SDL_Keyword_Paper'] == 0) & 
#     (df['field'].isin(['chemistry', 'materials_science'])) & 
#     (df['abstract_clean'].str.lower().str.contains(pattern))
# ].sample(n=600, random_state=42) # Match size of positives roughly
# hard_negatives['label'] = 0

# # C2. Random Negatives: Normal experimental science
# # These teach the model: "Normal Lab != Self-Driving Lab"
# random_negatives = df[
#     (df['SDL'] == 0) & 
#     (df['SDL_Keyword_Paper'] == 0) & 
#     (df['field'].isin(['chemistry', 'materials_science'])) & 
#     (~df.index.isin(hard_negatives.index)) # Don't duplicate
# ].sample(n=600, random_state=42)
# random_negatives['label'] = 0

# # D. Combine
# training_data = pd.concat([positives, hard_negatives, random_negatives])
# training_data = training_data.sample(frac=1, random_state=42).reset_index(drop=True)

# print("\n=== TRAINING DATA V2 STATISTICS ===")
# print(f"Positives (SDL): {len(positives)}")
# print(f"Hard Negatives (Simulations/AI): {len(hard_negatives)}")
# print(f"Random Negatives (Normal Science): {len(random_negatives)}")
# print(f"Total Training Rows: {len(training_data)}")

# # Save minimal file for training
# training_data[['article_id', 'text', 'label']].to_csv(OUTPUT_FILE, index=False)
# print(f"\nSaved clean training data to: {OUTPUT_FILE}")

# ### CREATING SPECIFIC DATASET (ITERATION 3)
# import pandas as pd
# import numpy as np

# # ==============================================================================
# # CONFIGURATION
# # ==============================================================================
# # INPUTS
# V2_TRAINING_FILE = "/project/def-kmcel/hridansh/openalex_project/data/scibert/training_data_v2.csv"
# CONFUSED_FILE = "/project/def-kmcel/hridansh/openalex_project/data/scibert/analysis/iteration_2/confused_papers_active_learning.csv"
# NEW_FINDS_FILE = "/project/def-kmcel/hridansh/openalex_project/data/scibert/analysis/iteration_2/high_confidence_new_finds.csv"

# # OUTPUT
# OUTPUT_FILE = "/project/def-kmcel/hridansh/openalex_project/data/scibert/training_data_v3.csv"

# # ==============================================================================
# # 1. LOAD DATA
# # ==============================================================================
# print(f"Loading V2 Training Data from {V2_TRAINING_FILE}...")
# df_train = pd.read_csv(V2_TRAINING_FILE)

# print(f"Loading Confused Papers from {CONFUSED_FILE}...")
# df_confused = pd.read_csv(CONFUSED_FILE)

# print(f"Loading New Finds from {NEW_FINDS_FILE}...")
# df_new_finds = pd.read_csv(NEW_FINDS_FILE)

# # ==============================================================================
# # 2. APPLY LABELS (Active Learning)
# # ==============================================================================
# print("\nApplying Auto-Labeling Rules...")

# # --- GROUP A: THE "NEW FINDS" (Score > 0.95) ---
# # VERDICT: These are REAL SDLs (Physical Automation).
# # ACTION: Label = 1
# new_positives = df_new_finds[['title', 'abstract']].copy()
# new_positives['label'] = 1
# # Create dummy IDs for tracking
# new_positives['article_id'] = ["AL_POS_" + str(i) for i in range(len(new_positives))]
# new_positives['text'] = new_positives['title'].fillna("") + " [SEP] " + new_positives['abstract'].fillna("")

# # --- GROUP B: THE "CONFUSED" PAPERS (Score 0.4 - 0.6) ---
# # VERDICT: These are "False Friends" (Software, Reviews, Simulations).
# # ACTION: Label = 0 (Hard Negatives)

# # SAFETY CHECK: If title contains "Robot", "Platform", or "Autonomous", DO NOT label as 0.
# # We skip them to avoid killing a real SDL that the model was just unsure about.
# safety_keywords = ['robot', 'platform', 'autonomous', 'self-driving', 'closed-loop']
# safe_mask = df_confused['title'].str.lower().apply(lambda x: any(k in str(x) for k in safety_keywords))

# # Filter out the "Safe" ones (Skip them), keep the rest as Negatives
# df_confused_safe = df_confused[~safe_mask].copy()
# skipped_count = safe_mask.sum()

# new_negatives = df_confused_safe[['title', 'abstract']].copy()
# new_negatives['label'] = 0
# new_negatives['article_id'] = ["AL_NEG_" + str(i) for i in range(len(new_negatives))]
# new_negatives['text'] = new_negatives['title'].fillna("") + " [SEP] " + new_negatives['abstract'].fillna("")

# print(f"Skipped {skipped_count} confused papers that looked 'Robotic' just in case.")

# # ==============================================================================
# # 3. MERGE AND SAVE
# # ==============================================================================
# print("\nMerging datasets...")
# # Concatenate: Old Training Data + New Positives + New Negatives
# v3_train = pd.concat([
#     df_train[['article_id', 'text', 'label']],
#     new_positives[['article_id', 'text', 'label']],
#     new_negatives[['article_id', 'text', 'label']]
# ], ignore_index=True)

# # Shuffle the deck
# v3_train = v3_train.sample(frac=1, random_state=42).reset_index(drop=True)

# print("\n=== TRAINING DATA V3 STATISTICS ===")
# print(f"Original V2 Rows:      {len(df_train)}")
# print(f"Added New Positives:   {len(new_positives)}")
# print(f"Added New Negatives:   {len(new_negatives)}")
# print(f"Total V3 Dataset:      {len(v3_train)}")
# print("-" * 30)
# print(f"Class Balance:         {v3_train['label'].value_counts().to_dict()}")

# v3_train.to_csv(OUTPUT_FILE, index=False)
# print(f"\nSaved V3 training data to: {OUTPUT_FILE}")


### ANALYSIS OF SCIBERT (ITERATION 3)
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
import os

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# 1. The NEW Scores File (v3) - Make sure this matches your output from run 3
SCORES_FILE = "/project/def-kmcel/hridansh/openalex_project/data/scibert/iteration_3_scibert_scores.csv"

# 2. The Original Text File (v21)
ORIGINAL_DATA_FILE = "/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_subset.csv"

OUTPUT_DIR = "/project/def-kmcel/hridansh/openalex_project/data/scibert/analysis/iteration_3"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==============================================================================
# 1. LOAD AND MERGE
# ==============================================================================
print(f"Loading NEW scores from {SCORES_FILE}...")
if not os.path.exists(SCORES_FILE):
    print(f"ERROR: Could not find {SCORES_FILE}. Did the training job finish?")
    exit()

df_scores = pd.read_csv(SCORES_FILE)

print(f"Loading original text from {ORIGINAL_DATA_FILE}...")
df_text = pd.read_csv(ORIGINAL_DATA_FILE, usecols=['article_id', 'abstract', 'title', 'SDL', 'SDL_Keyword_Paper'])

print("Merging datasets...")
df = pd.merge(df_scores, df_text, on='article_id', suffixes=('', '_orig'))

# Handle duplicate columns if any exist after merge
if 'SDL_orig' in df.columns:
    df['SDL'] = df['SDL_orig']
if 'SDL_Keyword_Paper_orig' in df.columns:
    df['SDL_Keyword_Paper'] = df['SDL_Keyword_Paper_orig']
    
# Fill NA text
df['title'] = df['title'].fillna("")
df['abstract'] = df['abstract'].fillna("")
df['full_text'] = df['title'] + " " + df['abstract']

# Define "Ground Truth"
df['Is_Known_SDL'] = ((df['SDL'] == 1) | (df['SDL_Keyword_Paper'] == 1)).astype(int)

print(f"Merged Data Shape: {df.shape}")

# ==============================================================================
# 2. SCORE DISTRIBUTION ANALYSIS
# ==============================================================================
print("\n=== 1. SCORE DISTRIBUTION (v3) ===")
known_sdl_scores = df[df['Is_Known_SDL'] == 1]['scibert_sdl_prob']
random_scores = df[df['Is_Known_SDL'] == 0]['scibert_sdl_prob']

print(f"Known SDLs (n={len(known_sdl_scores)}):")
print(f"  Mean Score: {known_sdl_scores.mean():.4f}")
print(f"  Median Score: {known_sdl_scores.median():.4f}")
print(f"  > 0.90: {(known_sdl_scores > 0.9).sum()} ({((known_sdl_scores > 0.9).sum()/len(known_sdl_scores))*100:.1f}%)")
print(f"  < 0.10 (Missed): {(known_sdl_scores < 0.1).sum()} ({((known_sdl_scores < 0.1).sum()/len(known_sdl_scores))*100:.1f}%)")

print(f"\nBackground Papers (n={len(random_scores)}):")
print(f"  Mean Score: {random_scores.mean():.4f}")
print(f"  > 0.90 (Potential New Finds): {(random_scores > 0.9).sum()}")
print(f"  (Previous v2 count was ~72,000. We want this lower!)")

# ==============================================================================
# 3. LEXICAL DIVERGENCE (Log-Odds Ratio)
# ==============================================================================
print("\n=== 2. DISTINCTIVE VOCABULARY (Log-Odds) ===")

# High Confidence SDL (>0.90) vs Low Confidence (<0.10)
high_conf_idx = df['scibert_sdl_prob'] > 0.90
low_conf_idx = df['scibert_sdl_prob'] < 0.10

if high_conf_idx.sum() < 10:
    print("Not enough high-confidence papers for lexical analysis.")
else:
    print("Extracting distinctive phrases...")
    vec = CountVectorizer(ngram_range=(2, 3), stop_words='english', min_df=5, max_features=50000)
    
    subset_df = pd.concat([df[high_conf_idx], df[low_conf_idx]])
    y = np.where(subset_df['scibert_sdl_prob'] > 0.90, 1, 0)
    
    X = vec.fit_transform(subset_df['full_text'])
    
    X_pos = X[y == 1]
    X_neg = X[y == 0]
    pos_counts = np.array(X_pos.sum(axis=0)).flatten() + 1
    neg_counts = np.array(X_neg.sum(axis=0)).flatten() + 1
    
    pos_norm = pos_counts / pos_counts.sum()
    neg_norm = neg_counts / neg_counts.sum()
    log_odds = np.log(pos_norm / neg_norm)
    
    vocab = {v: k for k, v in vec.vocabulary_.items()}
    
    # Top SDL Words
    print("\nTop 30 Phrases Driving High Scores (The 'Signal'):")
    print("(Check if 'Imitation Learning' and 'Robot' are gone/reduced)")
    for idx in log_odds.argsort()[::-1][:30]:
        print(f"  + {vocab[idx]} (Score: {log_odds[idx]:.2f})")
        
    # Top Non-SDL Words
    print("\nTop 20 Phrases Driving Low Scores (The 'Noise'):")
    for idx in log_odds.argsort()[:20]:
        print(f"  - {vocab[idx]} (Score: {log_odds[idx]:.2f})")

# ==============================================================================
# 4. TOPIC CONFOUNDING CHECK
# ==============================================================================
print("\n=== 3. TOPIC BIAS CHECK ===")
# We added 'simulation' and 'dft' to see if we fixed the bias
confounders = ['perovskite', 'battery', 'solar cell', 'drug discovery', 'catalysis', 'simulation', 'density functional', 'vasp']
print(f"{'Keyword':<20} | {'Avg Score':<10} | {'Count':<10}")
print("-" * 45)
for word in confounders:
    mask = df['full_text'].str.lower().str.contains(word)
    avg_score = df[mask]['scibert_sdl_prob'].mean()
    count = mask.sum()
    print(f"{word:<20} | {avg_score:.4f}     | {count:<10}")

# ==============================================================================
# 5. EXPORTS
# ==============================================================================
print("\n=== 4. EXPORTING FILES ===")

# Confused Papers (0.4 - 0.6)
confused_path = f"{OUTPUT_DIR}/confused_papers_active_learning.csv"
df[(df['scibert_sdl_prob'] > 0.40) & (df['scibert_sdl_prob'] < 0.60)][
    ['doi', 'title', 'abstract', 'scibert_sdl_prob']
].head(50).to_csv(confused_path, index=False)
print(f"Saved 'Confused' papers to: {confused_path}")

# New High Confidence
hall_path = f"{OUTPUT_DIR}/high_confidence_new_finds.csv"
df[(df['scibert_sdl_prob'] > 0.95) & (df['Is_Known_SDL'] == 0)][
    ['doi', 'title', 'abstract', 'scibert_sdl_prob']
].head(50).to_csv(hall_path, index=False)
print(f"Saved 'High Confidence New' papers to: {hall_path}")

# Hard Misses
missed_path = f"{OUTPUT_DIR}/hard_false_negatives.csv"
df[(df['scibert_sdl_prob'] < 0.20) & (df['Is_Known_SDL'] == 1)][
    ['doi', 'title', 'abstract', 'scibert_sdl_prob', 'SDL', 'SDL_Keyword_Paper']
].to_csv(missed_path, index=False)
print(f"Saved 'Hard Missed' papers to: {missed_path}")

print("\nDone.")