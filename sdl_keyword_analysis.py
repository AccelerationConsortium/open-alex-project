# import pandas as pd
# import re
# from collections import Counter
# import os

# # Configuration
# INPUT_CSV = "data/sdl/sdl_abstract.csv"
# OUTPUT_DIR = "data/sdl"

# # Load your existing keyword lists
# AI_KEYWORDS_FILE = "data/keywords/AI_Keywords.csv"
# ROBOTICS_KEYWORDS_FILE = "data/keywords/robotics_Keywords.csv"

# def load_keywords():
#     """Load AI and Robotics keywords from CSV files."""
#     ai_keywords = set()
#     robotics_keywords = set()
    
#     # Load AI keywords (comma-separated in one row)
#     if os.path.exists(AI_KEYWORDS_FILE):
#         with open(AI_KEYWORDS_FILE, 'r', encoding='utf-8') as f:
#             content = f.read()
#             # Split by commas and clean up
#             keywords = [kw.strip().lower() for kw in content.split(',')]
#             # Filter out empty strings
#             ai_keywords = set(kw for kw in keywords if kw and len(kw) > 0)
    
#     # Load Robotics keywords (one per line)
#     if os.path.exists(ROBOTICS_KEYWORDS_FILE):
#         robotics_df = pd.read_csv(ROBOTICS_KEYWORDS_FILE, header=None)
#         robotics_keywords = set(robotics_df.iloc[:, 0].str.lower().str.strip().tolist())
#         # Filter out empty strings
#         robotics_keywords = set(kw for kw in robotics_keywords if kw and len(kw) > 0)
    
#     return ai_keywords, robotics_keywords

# def clean_text(text):
#     """Clean and normalize text."""
#     if pd.isna(text) or text == "":
#         return ""
#     # Convert to lowercase
#     text = str(text).lower()
#     # Remove special characters but keep spaces and hyphens
#     text = re.sub(r'[^a-z0-9\s\-]', ' ', text)
#     # Replace multiple spaces with single space
#     text = re.sub(r'\s+', ' ', text)
#     return text.strip()

# def extract_ngrams(text, n=2):
#     """Extract n-grams from text."""
#     words = text.split()
#     ngrams = []
#     for i in range(len(words) - n + 1):
#         ngram = ' '.join(words[i:i+n])
#         ngrams.append(ngram)
#     return ngrams

# def is_stopword_ngram(ngram, common_words):
#     """Check if ngram is mostly stopwords."""
#     words = ngram.split()
#     # If more than half the words are common stopwords, skip it
#     stopword_count = sum(1 for w in words if w in common_words)
#     return stopword_count > len(words) / 2

# def count_missing_abstracts(df):
#     """Count papers with missing or empty abstracts."""
#     print("="*80)
#     print("MISSING ABSTRACT ANALYSIS")
#     print("="*80)
#     print()
    
#     total_papers = len(df)
#     missing_abstracts = df['abstract'].isna().sum()
#     empty_abstracts = (df['abstract'] == "").sum()
#     total_missing = missing_abstracts + empty_abstracts
    
#     print(f"Total SDL papers: {total_papers}")
#     print(f"Papers with missing abstracts (NaN): {missing_abstracts}")
#     print(f"Papers with empty abstracts (''): {empty_abstracts}")
#     print(f"Total without abstracts: {total_missing}")
#     print(f"Percentage: {total_missing/total_papers*100:.1f}%")
#     print()
    
#     # Breakdown by field
#     print("By field:")
#     for field in df['field'].unique():
#         field_df = df[df['field'] == field]
#         field_missing = field_df['abstract'].isna().sum() + (field_df['abstract'] == "").sum()
#         print(f"  {field}: {field_missing}/{len(field_df)} ({field_missing/len(field_df)*100:.1f}%)")
#     print()
    
#     # Check AI/Robotics classification of papers with abstracts
#     has_abstract = df[(df['abstract'].notna()) & (df['abstract'] != "")]
#     print(f"Papers WITH abstracts: {len(has_abstract)}")
#     print(f"  Classified as AI: {has_abstract['is_ai_paper'].sum()}")
#     print(f"  Classified as Robotics: {has_abstract['is_robotics_paper'].sum()}")
#     both = len(has_abstract[(has_abstract['is_ai_paper'] == 1) & (has_abstract['is_robotics_paper'] == 1)])
#     print(f"  Classified as BOTH: {both}")
    
#     neither = len(has_abstract[(has_abstract['is_ai_paper'] == 0) & (has_abstract['is_robotics_paper'] == 0)])
#     print(f"  NOT classified as AI or Robotics: {neither}")
#     print(f"  Percentage unclassified (with abstract): {neither/len(has_abstract)*100:.1f}%")
#     print()
    
#     return has_abstract, neither

# def has_technical_suffix(word):
#     """Check if word has technical/scientific suffix."""
#     technical_suffixes = [
#         'tion', 'ment', 'ized', 'ization', 'ology', 'ological', 
#         'ics', 'ical', 'ing', 'ated', 'ation', 'ive', 'al',
#         'ance', 'ence', 'ness', 'ity', 'sis', 'tic', 'ous'
#     ]
#     return any(word.endswith(suffix) for suffix in technical_suffixes)

# def is_technical_word(word):
#     """Check if a word is likely technical/scientific."""
#     # Long words are often technical
#     if len(word) > 8:
#         return True
#     # Has technical suffix
#     if has_technical_suffix(word):
#         return True
#     # Contains hyphen (compound technical terms)
#     if '-' in word and len(word) > 5:
#         return True
#     # Contains numbers (like "2d", "3d")
#     if any(c.isdigit() for c in word):
#         return True
#     return False

# def is_useful_ngram(ngram, stopwords, common_words):
#     """Enhanced filtering for n-grams."""
#     words = ngram.split()
    
#     # Must have at least one word longer than 5 characters
#     if not any(len(w) > 5 for w in words):
#         return False
    
#     # Must have at least one technical-sounding word
#     if not any(is_technical_word(w) for w in words):
#         return False
    
#     # Cannot be ALL common/stopwords
#     non_stopword_count = sum(1 for w in words if w not in stopwords and w not in common_words)
#     if non_stopword_count == 0:
#         return False
    
#     # Cannot start or end with stopword
#     if words[0] in stopwords or words[-1] in stopwords:
#         return False
    
#     return True

# def analyze_unmatched_papers(df, ai_keywords, robotics_keywords):
#     """Analyze papers that weren't matched to find missing keywords."""
    
#     print("="*80)
#     print("ANALYZING UNMATCHED PAPERS (Those with abstracts but no AI/Robotics match)")
#     print("="*80)
#     print()
    
#     # Get papers with abstracts but no classification
#     unmatched = df[
#         (df['abstract'].notna()) & 
#         (df['abstract'] != "") &
#         (df['is_ai_paper'] == 0) & 
#         (df['is_robotics_paper'] == 0)
#     ].copy()
    
#     print(f"Analyzing {len(unmatched)} unmatched papers...")
#     print()
    
#     # Enhanced stopwords - including common academic phrases
#     stopwords = {
#         'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
#         'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
#         'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
#         'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that',
#         'these', 'those', 'we', 'our', 'their', 'it', 'its', 'which', 'what',
#         'who', 'when', 'where', 'why', 'how', 'not', 'no', 'yes', 'than',
#         'such', 'into', 'through', 'during', 'before', 'after', 'above',
#         'below', 'between', 'among', 'all', 'both', 'each', 'few', 'more',
#         'most', 'other', 'some', 'only', 'own', 'same', 'so', 'than', 'too',
#         'very', 'one', 'two', 'three', 'also', 'well', 'here', 'there',
#         'then', 'now', 'them', 'they', 'she', 'he', 'her', 'his', 'you',
#         'your', 'been', 'make', 'made', 'get', 'got'
#     }
    
#     # Common academic words to filter
#     common_academic = {
#         'study', 'studies', 'paper', 'research', 'work', 'results', 'result',
#         'show', 'shown', 'showed', 'demonstrate', 'demonstrated', 'present',
#         'presented', 'describe', 'described', 'report', 'reported', 'propose',
#         'proposed', 'develop', 'developed', 'investigate', 'investigated',
#         'analysis', 'method', 'methods', 'approach', 'approaches', 'novel',
#         'new', 'different', 'various', 'several', 'many', 'number', 'provide',
#         'provided', 'important', 'significant', 'based', 'discussed', 'found',
#         'find', 'findings', 'obtained', 'observed', 'applied', 'potential',
#         'applications', 'application'
#     }
    
#     # Track paper-level frequency (not just word count)
#     word_papers = {}
#     bigram_papers = {}
#     trigram_papers = {}
    
#     for abstract in unmatched['abstract']:
#         cleaned = clean_text(abstract)
#         if not cleaned:
#             continue
        
#         words = cleaned.split()
        
#         # Track unique words per paper
#         seen_words = set()
#         for w in words:
#             if w not in stopwords and w not in common_academic and len(w) > 3:
#                 if is_technical_word(w):
#                     if w not in word_papers:
#                         word_papers[w] = {'count': 0, 'papers': 0}
#                     if w not in seen_words:
#                         word_papers[w]['papers'] += 1
#                         seen_words.add(w)
#                     word_papers[w]['count'] += 1
        
#         # Track unique bigrams per paper
#         bigrams = extract_ngrams(cleaned, 2)
#         seen_bigrams = set()
#         for bg in bigrams:
#             if is_useful_ngram(bg, stopwords, common_academic):
#                 if bg not in bigram_papers:
#                     bigram_papers[bg] = {'count': 0, 'papers': 0}
#                 if bg not in seen_bigrams:
#                     bigram_papers[bg]['papers'] += 1
#                     seen_bigrams.add(bg)
#                 bigram_papers[bg]['count'] += 1
        
#         # Track unique trigrams per paper
#         trigrams = extract_ngrams(cleaned, 3)
#         seen_trigrams = set()
#         for tg in trigrams:
#             if is_useful_ngram(tg, stopwords, common_academic):
#                 if tg not in trigram_papers:
#                     trigram_papers[tg] = {'count': 0, 'papers': 0}
#                 if tg not in seen_trigrams:
#                     trigram_papers[tg]['papers'] += 1
#                     seen_trigrams.add(tg)
#                 trigram_papers[tg]['count'] += 1
    
#     # No minimum frequency filter - show everything
    
#     # Sort by paper count (not total frequency)
#     sorted_words = sorted(word_papers.items(), key=lambda x: (x[1]['papers'], x[1]['count']), reverse=True)
#     sorted_bigrams = sorted(bigram_papers.items(), key=lambda x: (x[1]['papers'], x[1]['count']), reverse=True)
#     sorted_trigrams = sorted(trigram_papers.items(), key=lambda x: (x[1]['papers'], x[1]['count']), reverse=True)
    
#     # Save results
#     os.makedirs(OUTPUT_DIR, exist_ok=True)
    
#     # Save to CSV with both counts
#     top_words_df = pd.DataFrame([
#         {'word': word, 'total_count': data['count'], 'paper_count': data['papers']}
#         for word, data in sorted_words[:100]
#     ])
#     top_words_df.to_csv(f"{OUTPUT_DIR}/top_words_unmatched.csv", index=False)
    
#     top_bigrams_df = pd.DataFrame([
#         {'bigram': bigram, 'total_count': data['count'], 'paper_count': data['papers']}
#         for bigram, data in sorted_bigrams[:100]
#     ])
#     top_bigrams_df.to_csv(f"{OUTPUT_DIR}/top_bigrams_unmatched.csv", index=False)
    
#     top_trigrams_df = pd.DataFrame([
#         {'trigram': trigram, 'total_count': data['count'], 'paper_count': data['papers']}
#         for trigram, data in sorted_trigrams[:100]
#     ])
#     top_trigrams_df.to_csv(f"{OUTPUT_DIR}/top_trigrams_unmatched.csv", index=False)
    
#     # Print results
#     print("TOP 50 TECHNICAL WORDS in unmatched SDL abstracts:")
#     print("(Sorted by number of papers)")
#     print("-"*80)
#     for word, data in sorted_words[:50]:
#         in_ai = "✓ (in AI list)" if word in ai_keywords else ""
#         in_robotics = "✓ (in Robotics list)" if word in robotics_keywords else ""
#         marker = in_ai or in_robotics or "← NEW"
#         print(f"  {word:<30} Papers:{data['papers']:>3}  Total:{data['count']:>4}    {marker}")
#     print()
    
#     print("TOP 30 TECHNICAL BIGRAMS in unmatched SDL abstracts:")
#     print("(Sorted by number of papers)")
#     print("-"*80)
#     for bigram, data in sorted_bigrams[:30]:
#         words_in_bigram = bigram.split()
#         in_keywords = any(w in ai_keywords or w in robotics_keywords for w in words_in_bigram)
#         marker = "✓ (contains keyword)" if in_keywords else "← NEW"
#         print(f"  {bigram:<45} Papers:{data['papers']:>3}  Total:{data['count']:>4}    {marker}")
#     print()
    
#     print("TOP 20 TECHNICAL TRIGRAMS in unmatched SDL abstracts:")
#     print("(Sorted by number of papers)")
#     print("-"*80)
#     for trigram, data in sorted_trigrams[:20]:
#         words_in_trigram = trigram.split()
#         in_keywords = any(w in ai_keywords or w in robotics_keywords for w in words_in_trigram)
#         marker = "✓ (contains keyword)" if in_keywords else "← NEW"
#         print(f"  {trigram:<50} Papers:{data['papers']:>3}  Total:{data['count']:>4}    {marker}")
#     print()
    
#     print(f"Full results saved to {OUTPUT_DIR}/")
#     print()
    
#     return unmatched

# def analyze_matched_papers(df, ai_keywords, robotics_keywords):
#     """Analyze papers that WERE matched to understand what's working."""
    
#     print("="*80)
#     print("ANALYZING MATCHED PAPERS (For comparison)")
#     print("="*80)
#     print()
    
#     # Get papers that were matched
#     matched = df[
#         (df['abstract'].notna()) & 
#         (df['abstract'] != "") &
#         ((df['is_ai_paper'] == 1) | (df['is_robotics_paper'] == 1))
#     ].copy()
    
#     print(f"Analyzing {len(matched)} matched papers...")
#     print()
    
#     # Find which keywords are actually appearing
#     keyword_hits = Counter()
    
#     for abstract in matched['abstract']:
#         cleaned = clean_text(abstract)
#         if not cleaned:
#             continue
        
#         # Check each keyword
#         for keyword in ai_keywords.union(robotics_keywords):
#             if keyword in cleaned:
#                 keyword_hits[keyword] += 1
    
#     # Save and print top keywords actually found
#     top_keywords = pd.DataFrame(keyword_hits.most_common(50), 
#                                 columns=['keyword', 'frequency'])
#     top_keywords.to_csv(f"{OUTPUT_DIR}/top_keywords_found_in_matched.csv", index=False)
    
#     print("TOP 30 KEYWORDS actually found in matched papers:")
#     print("-"*80)
#     for keyword, count in keyword_hits.most_common(30):
#         in_ai = "(AI)" if keyword in ai_keywords else ""
#         in_robotics = "(Robotics)" if keyword in robotics_keywords else ""
#         print(f"  {keyword:<30} {count:>5}    {in_ai} {in_robotics}")
#     print()

# def sample_unmatched_papers(df, n=20):
#     """Save a random sample of unmatched papers for manual review."""
    
#     print("="*80)
#     print(f"SAMPLING {n} UNMATCHED PAPERS FOR MANUAL REVIEW")
#     print("="*80)
#     print()
    
#     unmatched = df[
#         (df['abstract'].notna()) & 
#         (df['abstract'] != "") &
#         (df['is_ai_paper'] == 0) & 
#         (df['is_robotics_paper'] == 0)
#     ].copy()
    
#     if len(unmatched) == 0:
#         print("No unmatched papers to sample!")
#         return
    
#     # Random sample
#     sample_size = min(n, len(unmatched))
#     sample = unmatched.sample(n=sample_size, random_state=42)
    
#     # Save to CSV for easy review
#     sample[['paper_id', 'field', 'publication_year', 'abstract']].to_csv(
#         f"{OUTPUT_DIR}/sample_unmatched_papers.csv", index=False
#     )
    
#     print(f"Saved {sample_size} random unmatched papers to:")
#     print(f"{OUTPUT_DIR}/sample_unmatched_papers.csv")
#     print()
#     print("Review these manually to understand why they didn't match!")
#     print()

# def main():
#     """Main analysis function."""
    
#     print()
#     print("="*80)
#     print("SDL PAPER CLASSIFICATION GAP ANALYSIS")
#     print("="*80)
#     print()
    
#     # Load data
#     print("Loading data...")
#     df = pd.read_csv(INPUT_CSV)
#     ai_keywords, robotics_keywords = load_keywords()
    
#     print(f"Loaded {len(df)} SDL papers")
#     print(f"Loaded {len(ai_keywords)} AI keywords")
#     print(f"Loaded {len(robotics_keywords)} Robotics keywords")
#     print()
    
#     # Analysis 1: Count missing abstracts
#     has_abstract_df, unclassified_count = count_missing_abstracts(df)
    
#     # Analysis 2: Analyze unmatched papers
#     unmatched_df = analyze_unmatched_papers(df, ai_keywords, robotics_keywords)
    
#     # Analysis 3: Analyze matched papers for comparison
#     analyze_matched_papers(df, ai_keywords, robotics_keywords)
    
#     # Analysis 4: Sample unmatched papers for manual review
#     sample_unmatched_papers(df, n=20)
    
#     print("="*80)
#     print("ANALYSIS COMPLETE!")
#     print("="*80)
#     print()
#     print("Generated files:")
#     print(f"  1. {OUTPUT_DIR}/top_words_unmatched.csv - Top 100 words in unmatched papers")
#     print(f"  2. {OUTPUT_DIR}/top_bigrams_unmatched.csv - Top 100 bigrams in unmatched papers")
#     print(f"  3. {OUTPUT_DIR}/top_trigrams_unmatched.csv - Top 100 trigrams in unmatched papers")
#     print(f"  4. {OUTPUT_DIR}/top_keywords_found_in_matched.csv - Keywords found in matched papers")
#     print(f"  5. {OUTPUT_DIR}/sample_unmatched_papers.csv - 20 random unmatched papers for review")
#     print()
#     print("NEXT STEPS:")
#     print("  1. Review the top words/bigrams/trigrams to identify missing keywords")
#     print("  2. Manually read the sample_unmatched_papers.csv to understand patterns")
#     print("  3. Add promising terms to your keyword lists")
#     print("  4. Re-run classification and measure improvement")
#     print()

# if __name__ == "__main__":
# #     main()
import pandas as pd
import re
import os

#==============================================================================
# CHANGE THESE PATHS TO YOUR KEYWORD FILES
#==============================================================================
AI_KEYWORDS_OLD_FILE = 'data/keywords/AI_Keywords.csv'  # Your original AI keywords
ROBOTICS_KEYWORDS_OLD_FILE = 'data/keywords/robotics_Keywords.csv'  # Your original Robotics keywords
AI_KEYWORDS_NEW_FILE = 'data/keywords/AI_Keywords_generated.csv'  # New extensive AI keywords
ROBOTICS_KEYWORDS_NEW_FILE = 'data/keywords/robotics_Keywords_generated.csv'  # New extensive Robotics keywords

# SDL papers file (should have 'title' column - use the file from extract_sdl_with_titles.py)
SDL_FILE = 'data/sdl/sdl_abstract.csv'  # File with title, abstract, etc.
#==============================================================================

# Load SDL papers
df = pd.read_csv(SDL_FILE)

# Get ALL papers (not just those with abstracts)
# We'll check title+abstract for papers with abstracts
# And check title-only for papers without abstracts
all_papers = df.copy()

print("="*80)
print("TESTING COMBINED (OLD + NEW) KEYWORD LISTS ON SDL PAPERS")
print("="*80)
print()
print(f"Total SDL papers: {len(all_papers)}")
has_abstract_count = all_papers['abstract'].notna().sum()
no_abstract_count = all_papers['abstract'].isna().sum()
print(f"Papers WITH abstract: {has_abstract_count} (will check title + abstract)")
print(f"Papers WITHOUT abstract: {no_abstract_count} (will check title only)")
print()
print(f"Currently classified as AI: {all_papers['is_ai_paper'].sum()}")
print(f"Currently classified as Robotics: {all_papers['is_robotics_paper'].sum()}")
both_current = len(all_papers[(all_papers['is_ai_paper'] == 1) & (all_papers['is_robotics_paper'] == 1)])
print(f"Currently classified as BOTH: {both_current}")
neither_current = len(all_papers[(all_papers['is_ai_paper'] == 0) & (all_papers['is_robotics_paper'] == 0)])
print(f"Currently NOT classified: {neither_current}")
print()

# Check if title column exists
has_title = 'title' in df.columns
if has_title:
    print("✓ Title column found - will check keywords in titles")
    has_title_count = all_papers['title'].notna().sum()
    print(f"  Papers with titles: {has_title_count}")
else:
    print("✗ Title column not found - will only check abstract")
    print("  (Use extract_sdl_with_titles.py to create file with titles)")
print()

# Load OLD keywords
ai_keywords_old = set()
robotics_keywords_old = set()

print("Loading ORIGINAL keywords...")
# Load old AI keywords (comma-separated format)
if os.path.exists(AI_KEYWORDS_OLD_FILE):
    with open(AI_KEYWORDS_OLD_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        keywords = [kw.strip().lower() for kw in content.split(',')]
        ai_keywords_old = set(kw for kw in keywords if kw and len(kw) > 0)
    print(f"  ✓ Loaded {len(ai_keywords_old)} original AI keywords")
else:
    print(f"  ✗ Could not find: {AI_KEYWORDS_OLD_FILE}")

# Load old Robotics keywords (one per line format)
if os.path.exists(ROBOTICS_KEYWORDS_OLD_FILE):
    robotics_df = pd.read_csv(ROBOTICS_KEYWORDS_OLD_FILE, header=None)
    robotics_keywords_old = set(robotics_df.iloc[:, 0].str.lower().str.strip().tolist())
    robotics_keywords_old = set(kw for kw in robotics_keywords_old if kw and len(kw) > 0)
    print(f"  ✓ Loaded {len(robotics_keywords_old)} original Robotics keywords")
else:
    print(f"  ✗ Could not find: {ROBOTICS_KEYWORDS_OLD_FILE}")

# Load NEW extensive keywords
ai_keywords_new = set()
robotics_keywords_new = set()

print()
print("Loading NEW extensive keywords...")
if os.path.exists(AI_KEYWORDS_NEW_FILE):
    with open(AI_KEYWORDS_NEW_FILE, 'r') as f:
        ai_keywords_new = set([line.strip().lower() for line in f if line.strip()])
    print(f"  ✓ Loaded {len(ai_keywords_new)} new AI keywords")
else:
    print(f"  ✗ Could not find: {AI_KEYWORDS_NEW_FILE}")

if os.path.exists(ROBOTICS_KEYWORDS_NEW_FILE):
    with open(ROBOTICS_KEYWORDS_NEW_FILE, 'r') as f:
        robotics_keywords_new = set([line.strip().lower() for line in f if line.strip()])
    print(f"  ✓ Loaded {len(robotics_keywords_new)} new Robotics keywords")
else:
    print(f"  ✗ Could not find: {ROBOTICS_KEYWORDS_NEW_FILE}")

# Combine old and new keywords
ai_keywords = ai_keywords_old.union(ai_keywords_new)
robotics_keywords = robotics_keywords_old.union(robotics_keywords_new)

print()
print("="*80)
print("COMBINED KEYWORDS SUMMARY")
print("="*80)
print(f"AI Keywords:")
print(f"  Original: {len(ai_keywords_old)}")
print(f"  New: {len(ai_keywords_new)}")
print(f"  Combined (unique): {len(ai_keywords)}")
print(f"  Duplicates removed: {len(ai_keywords_old) + len(ai_keywords_new) - len(ai_keywords)}")
print()
print(f"Robotics Keywords:")
print(f"  Original: {len(robotics_keywords_old)}")
print(f"  New: {len(robotics_keywords_new)}")
print(f"  Combined (unique): {len(robotics_keywords)}")
print(f"  Duplicates removed: {len(robotics_keywords_old) + len(robotics_keywords_new) - len(robotics_keywords)}")
print("="*80)
print()

def check_keywords(text, keywords):
    """Check if any keyword appears in text (title or abstract)."""
    if pd.isna(text):
        return False
    text_lower = text.lower()
    for keyword in keywords:
        # Use word boundary matching for single words, substring for phrases
        if ' ' in keyword or '-' in keyword:
            # Multi-word phrase or hyphenated - use substring match
            if keyword in text_lower:
                return True
        else:
            # Single word - use word boundary
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                return True
    return False

# Test new classifications
# For papers WITH abstract: check title OR abstract
# For papers WITHOUT abstract: check title only
if has_title:
    print("Classifying papers based on title and/or abstract...")
    all_papers['new_ai'] = all_papers.apply(
        lambda row: (
            check_keywords(row.get('title', ''), ai_keywords) or 
            (check_keywords(row.get('abstract', ''), ai_keywords) if pd.notna(row.get('abstract')) else False)
        ), 
        axis=1
    )
    all_papers['new_robotics'] = all_papers.apply(
        lambda row: (
            check_keywords(row.get('title', ''), robotics_keywords) or 
            (check_keywords(row.get('abstract', ''), robotics_keywords) if pd.notna(row.get('abstract')) else False)
        ), 
        axis=1
    )
else:
    print("Classifying papers based on abstract only (no title column)...")
    all_papers['new_ai'] = all_papers['abstract'].apply(lambda x: check_keywords(x, ai_keywords) if pd.notna(x) else False)
    all_papers['new_robotics'] = all_papers['abstract'].apply(lambda x: check_keywords(x, robotics_keywords) if pd.notna(x) else False)
print()

# Calculate results
new_ai_count = all_papers['new_ai'].sum()
new_robotics_count = all_papers['new_robotics'].sum()
new_both = len(all_papers[(all_papers['new_ai']) & (all_papers['new_robotics'])])
new_neither = len(all_papers[(~all_papers['new_ai']) & (~all_papers['new_robotics'])])

print("="*80)
print("RESULTS WITH COMBINED KEYWORD LISTS")
if has_title:
    print("(Checked in title and/or abstract)")
else:
    print("(Checked in abstract only)")
print("="*80)
print(f"Would classify as AI: {new_ai_count} (currently: {all_papers['is_ai_paper'].sum()})")
print(f"Would classify as Robotics: {new_robotics_count} (currently: {all_papers['is_robotics_paper'].sum()})")
print(f"Would classify as BOTH: {new_both} (currently: {both_current})")
print(f"Would remain UNCLASSIFIED: {new_neither} (currently: {neither_current})")
print()

# Calculate improvement
ai_improvement = new_ai_count - all_papers['is_ai_paper'].sum()
robotics_improvement = new_robotics_count - all_papers['is_robotics_paper'].sum()
unclassified_reduction = neither_current - new_neither

print("="*80)
print("IMPROVEMENT")
print("="*80)
print(f"Additional AI papers found: {ai_improvement} (+{ai_improvement/all_papers['is_ai_paper'].sum()*100:.1f}%)")
print(f"Additional Robotics papers found: {robotics_improvement} (+{robotics_improvement/all_papers['is_robotics_paper'].sum()*100:.1f}%)")
print(f"Reduction in unclassified papers: {unclassified_reduction} (-{unclassified_reduction/neither_current*100:.1f}%)")
print()

# Breakdown by current classification status
print("="*80)
print("BREAKDOWN OF NEWLY FOUND PAPERS")
print("="*80)

# Papers currently unclassified that would be found
currently_unclassified = all_papers[(all_papers['is_ai_paper'] == 0) & (all_papers['is_robotics_paper'] == 0)]
newly_found_ai = currently_unclassified['new_ai'].sum()
newly_found_robotics = currently_unclassified['new_robotics'].sum()
newly_found_both = len(currently_unclassified[(currently_unclassified['new_ai']) & (currently_unclassified['new_robotics'])])
still_unclassified = len(currently_unclassified[(~currently_unclassified['new_ai']) & (~currently_unclassified['new_robotics'])])

print(f"From {len(currently_unclassified)} currently unclassified papers:")
print(f"  Would find {newly_found_ai} as AI")
print(f"  Would find {newly_found_robotics} as Robotics")
print(f"  Would find {newly_found_both} as BOTH")
print(f"  Would remain unclassified: {still_unclassified}")
print()

# Percentage coverage
total_papers = len(all_papers)
print("="*80)
print("COVERAGE ANALYSIS")
print("="*80)
print(f"AI coverage: {new_ai_count}/{total_papers} ({new_ai_count/total_papers*100:.1f}%)")
print(f"Robotics coverage: {new_robotics_count}/{total_papers} ({new_robotics_count/total_papers*100:.1f}%)")
print(f"Either AI or Robotics: {new_ai_count + new_robotics_count - new_both}/{total_papers} ({(new_ai_count + new_robotics_count - new_both)/total_papers*100:.1f}%)")
print(f"Both AI and Robotics: {new_both}/{total_papers} ({new_both/total_papers*100:.1f}%)")
print(f"Neither: {new_neither}/{total_papers} ({new_neither/total_papers*100:.1f}%)")
print()

# Save papers where NOT (both AI and Robotics are true)
# This should be from ALL papers
papers_to_save = all_papers[~(all_papers['new_ai'] & all_papers['new_robotics'])].copy()
papers_to_save_count = len(papers_to_save)

if papers_to_save_count > 0:
    print("="*80)
    print(f"SAVING {papers_to_save_count} PAPERS WHERE NOT BOTH AI AND ROBOTICS")
    print(f"(From ALL {total_papers} papers)")
    print("="*80)
    
    # Get all papers from original dataframe
    unmatched_output = df[df['paper_id'].isin(papers_to_save['paper_id'])][
        ['paper_id', 'field', 'publication_year', 'abstract', 'authors', 'is_ai_paper', 'is_robotics_paper']
    ].copy()
    
    unmatched_output.to_csv('unmatched_papers.csv', index=False)
    
    # Count breakdown
    only_ai = len(papers_to_save[(papers_to_save['new_ai']) & (~papers_to_save['new_robotics'])])
    only_robotics = len(papers_to_save[(~papers_to_save['new_ai']) & (papers_to_save['new_robotics'])])
    neither = len(papers_to_save[(~papers_to_save['new_ai']) & (~papers_to_save['new_robotics'])])
    
    print(f"Breakdown:")
    print(f"  AI only (not Robotics): {only_ai}")
    print(f"  Robotics only (not AI): {only_robotics}")
    print(f"  Neither AI nor Robotics: {neither}")
    print(f"  Total saved: {papers_to_save_count}")
    print(f"\nVerification: {only_ai} + {only_robotics} + {neither} = {only_ai + only_robotics + neither}")
    print(f"Should equal total saved: {papers_to_save_count}")
    print(f"\nSaved to: unmatched_papers.csv")
    print()
else:
    print("="*80)
    print("ALL PAPERS MATCHED AS BOTH AI AND ROBOTICS!")
    print("="*80)
    print("No papers to save.")
    print()

print("="*80)
print("FINAL SUMMARY")
print("="*80)
print(f"The combined keyword lists would:")
print(f"  - Classify {new_ai_count}/{total_papers} papers as AI ({new_ai_count/total_papers*100:.1f}%)")
print(f"  - Classify {new_robotics_count}/{total_papers} papers as Robotics ({new_robotics_count/total_papers*100:.1f}%)")
print(f"  - Classify {new_both}/{total_papers} papers as BOTH ({new_both/total_papers*100:.1f}%)")
print(f"  - Leave only {new_neither}/{total_papers} papers unclassified ({new_neither/total_papers*100:.1f}%)")
print(f"  - Improvement: {unclassified_reduction} fewer unclassified papers (-{unclassified_reduction/neither_current*100:.1f}%)")
print()
print(f"Papers saved to unmatched_papers.csv: those not classified as BOTH AI and Robotics")
print("="*80)