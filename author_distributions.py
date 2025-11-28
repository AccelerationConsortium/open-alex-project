"""
Code to get information about author field/topic distributions.
For all authors in regression dataset (specifically where papers are present in SDL Journals & Topics.),
this will get from Author table the info about all topics and fields the author has published in.
It will also filter to not consider authors from any papers with missing author_count, publication_year, or field.
"""

import pandas as pd
import json
from pathlib import Path
from collections import defaultdict, Counter

# ============================================
# CONFIGURATION
# ============================================

# Input file
REGRESSION_DATA = "data/regression/regression_dataset.csv"

# SDL venue lists (same as your extraction script)
SDL_JOURNALS_FILE = "data/sdl/sdl_journals.txt"
SDL_TOPICS_FILE = "data/sdl/sdl_primary_topics.txt"

# Output file
OUTPUT_FILE = "data/author/all_authors_top_metrics.csv"

# Chunk size for reading
CHUNK_SIZE = 500000

# ============================================
# STEP 1: LOAD SDL VENUES
# ============================================

def load_sdl_venues():
    """Load SDL journals and topics from files."""
    print("\n" + "="*60)
    print("LOADING SDL VENUE LISTS")
    print("="*60)
    
    sdl_journals = []
    sdl_topics = []
    
    if Path(SDL_JOURNALS_FILE).exists():
        with open(SDL_JOURNALS_FILE, 'r') as f:
            sdl_journals = [line.strip() for line in f if line.strip()]
        print(f"✓ Loaded {len(sdl_journals)} SDL journals")
    else:
        print(f"⚠ Warning: SDL journals file not found at {SDL_JOURNALS_FILE}")
    
    if Path(SDL_TOPICS_FILE).exists():
        with open(SDL_TOPICS_FILE, 'r') as f:
            sdl_topics = [line.strip() for line in f if line.strip()]
        print(f"✓ Loaded {len(sdl_topics)} SDL topics")
    else:
        print(f"⚠ Warning: SDL topics file not found at {SDL_TOPICS_FILE}")
    
    return set(sdl_journals), set(sdl_topics)

# ============================================
# STEP 2: BUILD AUTHOR PROFILES
# ============================================

def build_author_profiles(sdl_journals, sdl_topics):
    """
    Build author profiles from papers in SDL journals AND topics.
    For each author (first, last, and corresponding), track counts of fields, topics, and journals.
    """
    print("\n" + "="*60)
    print("BUILDING AUTHOR PROFILES (ALL AUTHORS)")
    print("="*60)
    
    # Dictionary to store author profiles
    # Structure: {author_id: {'fields': Counter(), 'topics': Counter(), 'journals': Counter(), 'has_cs_experience': bool}}
    author_profiles = defaultdict(lambda: {
        'fields': Counter(),
        'topics': Counter(),
        'journals': Counter(),
        'has_cs_experience': False
    })
    
    total_papers = 0
    filtered_papers = 0
    papers_processed = 0
    
    print("\nProcessing chunks...")
    
    for chunk_num, chunk in enumerate(pd.read_csv(
        REGRESSION_DATA,
        sep=',',
        chunksize=CHUNK_SIZE,
        usecols=['journal', 'primary_topic', 'first_author_id', 'last_author_id', 'corresponding_author_id',
                'field', 'author_count', 'publication_year', 'comp_sci_experience_paper']
    ), start=1):
        
        total_papers += len(chunk)
        
        # Filter to papers in SDL journals AND topics
        filtered_chunk = chunk[
            (chunk['journal'].isin(sdl_journals)) & 
            (chunk['primary_topic'].isin(sdl_topics))
        ]
        
        filtered_papers += len(filtered_chunk)
        
        # Remove papers with missing critical values
        filtered_chunk = filtered_chunk.dropna(subset=['author_count', 'publication_year', 'field'])
        
        # Process each paper
        for _, row in filtered_chunk.iterrows():
            # Get all author IDs for this paper
            author_ids = []
            
            if pd.notna(row['first_author_id']):
                author_ids.append(row['first_author_id'])
            
            if pd.notna(row['last_author_id']):
                author_ids.append(row['last_author_id'])
            
            if pd.notna(row['corresponding_author_id']) and row['corresponding_author_id'] != '':
                author_ids.append(row['corresponding_author_id'])
            
            # Skip if no authors
            if not author_ids:
                continue
            
            papers_processed += 1
            
            # Update profile for each author
            for author_id in author_ids:
                # Update author profile
                if pd.notna(row['field']):
                    author_profiles[author_id]['fields'][row['field']] += 1
                
                if pd.notna(row['primary_topic']):
                    author_profiles[author_id]['topics'][row['primary_topic']] += 1
                
                if pd.notna(row['journal']):
                    author_profiles[author_id]['journals'][row['journal']] += 1
                
                # Update CS experience
                if row['comp_sci_experience_paper'] == 1:
                    author_profiles[author_id]['has_cs_experience'] = True
        
        # Progress update
        if chunk_num % 10 == 0:
            print(f"  Chunk {chunk_num}: {papers_processed:,} papers processed, {len(author_profiles):,} unique authors...")
    
    print(f"\n✓ Finished processing")
    print(f"  Total papers in dataset: {total_papers:,}")
    print(f"  Papers in SDL journals AND topics: {filtered_papers:,}")
    print(f"  Papers with valid authors: {papers_processed:,}")
    print(f"  Unique authors: {len(author_profiles):,}")
    
    return author_profiles, papers_processed

# ============================================
# STEP 3: SAVE RESULTS
# ============================================

def save_author_profiles(author_profiles):
    """Convert author profiles to DataFrame and save."""
    print("\n" + "="*60)
    print("SAVING AUTHOR PROFILES")
    print("="*60)
    
    results = []
    
    for author_id, profile in author_profiles.items():
        # Calculate totals
        total_papers = sum(profile['fields'].values())
        
        # Get top field, topic, and journal (most common)
        top_field = profile['fields'].most_common(1)[0][0] if profile['fields'] else None
        top_topic = profile['topics'].most_common(1)[0][0] if profile['topics'] else None
        top_journal = profile['journals'].most_common(1)[0][0] if profile['journals'] else None
        
        # Convert counters to JSON strings
        result = {
            'author_id': author_id,
            'total_papers': total_papers,
            'top_field': top_field,
            'top_topic': top_topic,
            'top_journal': top_journal,
            'has_cs_experience': int(profile['has_cs_experience']),
            'field_counts': json.dumps(dict(profile['fields'])),
            'topic_counts': json.dumps(dict(profile['topics'])),
            'journal_counts': json.dumps(dict(profile['journals'])),
            'num_unique_fields': len(profile['fields']),
            'num_unique_topics': len(profile['topics']),
            'num_unique_journals': len(profile['journals'])
        }
        results.append(result)
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Sort by total papers (descending)
    df = df.sort_values('total_papers', ascending=False)
    
    # Save to CSV
    df.to_csv(OUTPUT_FILE, index=False)
    
    print(f"✓ Saved {len(df):,} author profiles to {OUTPUT_FILE}")
    
    # Print summary statistics
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    print(f"Total authors: {len(df):,}")
    print(f"\nPapers per author:")
    print(f"  Mean: {df['total_papers'].mean():.1f}")
    print(f"  Median: {df['total_papers'].median():.0f}")
    print(f"  Min: {df['total_papers'].min()}")
    print(f"  Max: {df['total_papers'].max()}")
    
    print(f"\nCS Experience:")
    cs_count = df['has_cs_experience'].sum()
    print(f"  Authors with CS experience: {cs_count:,} ({cs_count/len(df)*100:.2f}%)")
    print(f"  Authors without CS experience: {len(df)-cs_count:,} ({(len(df)-cs_count)/len(df)*100:.2f}%)")
    
    print(f"\nField diversity:")
    print(f"  Mean unique fields: {df['num_unique_fields'].mean():.2f}")
    print(f"  Max unique fields: {df['num_unique_fields'].max()}")
    print(f"\nTopic diversity:")
    print(f"  Mean unique topics: {df['num_unique_topics'].mean():.1f}")
    print(f"  Max unique topics: {df['num_unique_topics'].max()}")
    print(f"\nJournal diversity:")
    print(f"  Mean unique journals: {df['num_unique_journals'].mean():.1f}")
    print(f"  Max unique journals: {df['num_unique_journals'].max()}")
    print("="*60)

# ============================================
# MAIN
# ============================================

def main():
    print("="*60)
    print("BUILDING AUTHOR DIVERSITY PROFILES - ALL AUTHORS")
    print("="*60)
    
    # Check if input file exists
    if not Path(REGRESSION_DATA).exists():
        print(f"\n❌ ERROR: Regression dataset not found at {REGRESSION_DATA}")
        return
    
    print(f"\n📂 Reading from: {REGRESSION_DATA}")
    print(f"📝 Output to: {OUTPUT_FILE}")
    
    # Step 1: Load SDL venues
    sdl_journals, sdl_topics = load_sdl_venues()
    
    if not sdl_journals or not sdl_topics:
        print("\n❌ ERROR: Could not load SDL venue lists")
        return
    
    # Step 2: Build author profiles
    author_profiles, papers_processed = build_author_profiles(sdl_journals, sdl_topics)
    
    # Step 3: Save results
    save_author_profiles(author_profiles)
    
    print(f"\n✅ Complete! Output saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
