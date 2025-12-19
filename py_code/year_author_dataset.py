import pandas as pd
import json
from collections import Counter
import numpy as np
from pathlib import Path
import sys
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================
batch_size = 500000
years = range(2012, 2026)

project_dir = Path("/project/def-kmcel/hridansh/openalex_project")
data_dir = project_dir / "data/fields"

fields = {
    'chemistry': data_dir / "chemistry",
    'materials_science': data_dir / "material_science", 
    'engineering': data_dir / "engineering",
    'computer_science': data_dir / "computer_science"
}

output_dir = project_dir / "data/yearly_data/test"
output_dir.mkdir(parents=True, exist_ok=True)
output_csv = output_dir / "author_metrics_yearly.csv"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clean_id(raw_id):
    """Remove URL prefix from OpenAlex IDs."""
    if not raw_id:
        return ''
    return str(raw_id).replace('https://openalex.org/', '')


def parse_authorships(raw_data_json):
    """Extract authorship information, positions, and institutions."""
    if pd.isna(raw_data_json) or raw_data_json == '':
        return []
    
    try:
        data = json.loads(raw_data_json)
        authorships = data.get('authorships', [])
        num_authors = len(authorships)
        result = []
        
        for idx, authorship in enumerate(authorships):
            author = authorship.get('author', {})
            author_id = clean_id(author.get('id'))
            
            if not author_id:
                continue
            
            institutions = []
            for inst in authorship.get('institutions', []):
                inst_id = clean_id(inst.get('id'))
                if inst_id:
                    institutions.append(inst_id)
            
            result.append({
                'author_id': author_id,
                'author_name': author.get('display_name', ''),
                'is_first': (idx == 0),
                'is_last': (idx == num_authors - 1),
                'institutions': institutions
            })
        return result
    except:
        return []


def parse_metadata_granular(raw_data_json):
    """Extract topic, journal, corr_ids, citation count, and publication year."""
    topic, journal, corr_ids, citations, pub_year = None, None, [], 0, None
    
    if pd.isna(raw_data_json) or raw_data_json == '':
        return topic, journal, corr_ids, citations, pub_year

    try:
        data = json.loads(raw_data_json)
        
        # Topic (Primary)
        topics = data.get('topics', [])
        topic = topics[0].get('display_name') if topics else None
        
        # Journal
        journal = data.get('primary_location', {}).get('source', {}).get('display_name')
        
        # Corresponding Authors
        corr_ids = [clean_id(aid) for aid in data.get('corresponding_author_ids', []) if aid]
        
        # Citations
        citations = data.get('cited_by_count', 0) or 0
        
        # Publication Year
        pub_date = data.get('publication_date')
        if pub_date:
            try:
                pub_year = int(pub_date.split('-')[0])
            except:
                pass
        
    except:
        pass

    return topic, journal, corr_ids, citations, pub_year


# ============================================================================
# PAPER DATA STRUCTURE
# ============================================================================

def init_paper_entry():
    """Factory function for storing individual paper data."""
    return {
        'year': None,
        'field': '',
        'topic': '',
        'journal': '',
        'citations': 0,
        'institutions': set(),
        'is_first': False,
        'is_last': False,
        'is_corresponding': False,
        'is_sdl': False,
        'is_ai': False,
        'is_robotics': False
    }


# ============================================================================
# MAIN BUILD FUNCTION
# ============================================================================

def build_author_yearly_dataset(years):
    """
    Build author-level dataset with yearly cumulative metrics.
    Each row represents one author in one year.
    """
    
    print("Building yearly author dataset with cumulative metrics")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Store all papers for each author (we'll aggregate by year later)
    # Structure: {author_id: [list of paper entries]}
    all_author_papers = {}
    
    total_papers_processed = 0
    
    # ========================================================================
    # PHASE 1: Collect all papers for each author
    # ========================================================================
    
    print("PHASE 1: Collecting all papers by author")
    print("=" * 70)
    
    for field_name, field_path in fields.items():
        print(f"\nProcessing {field_name}")
        
        field_papers = 0
        
        if not field_path.exists():
            print(f"  Warning: Path not found {field_path}")
            continue

        for year in years:
            # Handle filename variations
            tsv_files = [
                field_path / f"{field_name}_{year}.tsv",
                field_path / f"{field_name.replace('_', '')}_{year}.tsv"
            ]
            tsv_file = next((f for f in tsv_files if f.exists()), None)
            
            if not tsv_file:
                continue

            year_papers = 0
            
            try:
                # Determine available columns
                sample = pd.read_csv(tsv_file, sep='\t', nrows=1)
                available_cols = set(sample.columns)
                required_cols = ['raw_data', 'SDL', 'AI_Paper', 'Robotics_Paper']
                use_cols = [c for c in required_cols if c in available_cols]

                if 'raw_data' not in use_cols:
                    continue

                for chunk in pd.read_csv(
                    tsv_file, 
                    sep='\t', 
                    usecols=use_cols,
                    chunksize=batch_size, 
                    low_memory=False,
                    on_bad_lines='skip'
                ):
                    for i in chunk.index:
                        try:
                            raw_data = chunk.at[i, 'raw_data']
                            
                            # Parse authorship
                            authorships = parse_authorships(raw_data)
                            if not authorships:
                                continue
                            
                            # Parse metadata
                            topic, journal, corr_ids, citations, pub_year = parse_metadata_granular(raw_data)
                            
                            # Skip if we don't have publication year
                            if not pub_year:
                                continue
                            
                            # Get flags
                            is_sdl = chunk.at[i, 'SDL'] == 1 if 'SDL' in chunk else False
                            is_ai = chunk.at[i, 'AI_Paper'] == 1 if 'AI_Paper' in chunk else False
                            is_robotics = chunk.at[i, 'Robotics_Paper'] == 1 if 'Robotics_Paper' in chunk else False
                            
                            # Create paper entry for each author
                            for auth in authorships:
                                a_id = auth['author_id']
                                
                                if a_id not in all_author_papers:
                                    all_author_papers[a_id] = []
                                
                                paper_data = {
                                    'year': pub_year,
                                    'author_name': auth['author_name'],
                                    'field': field_name,
                                    'topic': topic,
                                    'journal': journal,
                                    'citations': citations,
                                    'institutions': auth['institutions'],
                                    'is_first': auth['is_first'],
                                    'is_last': auth['is_last'],
                                    'is_corresponding': a_id in corr_ids,
                                    'is_sdl': is_sdl,
                                    'is_ai': is_ai,
                                    'is_robotics': is_robotics
                                }
                                
                                all_author_papers[a_id].append(paper_data)
                            
                            year_papers += 1
                            
                        except Exception:
                            continue
                
                print(f"  Year {year}: {year_papers:,} papers processed")
                field_papers += year_papers
                
            except Exception as e:
                print(f"  Year {year}: Error - {str(e)[:100]}")
                continue
        
        print(f"  Field total: {field_papers:,} papers")
        total_papers_processed += field_papers

    print(f"\nTotal papers collected: {total_papers_processed:,}")
    print(f"Total unique authors: {len(all_author_papers):,}")
    
    # ========================================================================
    # PHASE 2: Generate yearly cumulative metrics
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("PHASE 2: Generating yearly cumulative metrics")
    print("=" * 70)
    
    rows = []
    authors_processed = 0
    
    for author_id, papers in all_author_papers.items():
        authors_processed += 1
        
        if authors_processed % 50000 == 0:
            print(f"  Processed {authors_processed:,} / {len(all_author_papers):,} authors...")
        
        # Sort papers by year
        papers_sorted = sorted(papers, key=lambda x: x['year'])
        
        # Get all years this author was active
        author_years = sorted(set(p['year'] for p in papers_sorted))
        
        # For each year, calculate cumulative metrics
        for target_year in author_years:
            # Get all papers up to and including target_year
            papers_to_date = [p for p in papers_sorted if p['year'] <= target_year]
            
            if not papers_to_date:
                continue
            
            # Get most common author name
            author_name = Counter([p['author_name'] for p in papers_to_date if p['author_name']]).most_common(1)[0][0] if papers_to_date else ''
            
            # Count metrics
            total_papers = len(papers_to_date)
            first_author_papers = sum(1 for p in papers_to_date if p['is_first'])
            last_author_papers = sum(1 for p in papers_to_date if p['is_last'])
            corresponding_author_papers = sum(1 for p in papers_to_date if p['is_corresponding'])
            
            # Citation metrics
            total_citations = sum(p['citations'] for p in papers_to_date)
            citations_list = [p['citations'] for p in papers_to_date]
            avg_citations = np.mean(citations_list) if citations_list else 0
            
            # Field/topic/journal metrics
            fields_list = [p['field'] for p in papers_to_date if p['field']]
            topics_list = [p['topic'] for p in papers_to_date if p['topic']]
            journals_list = [p['journal'] for p in papers_to_date if p['journal']]
            
            top_field, top_field_count = Counter(fields_list).most_common(1)[0] if fields_list else ('', 0)
            top_topic, top_topic_count = Counter(topics_list).most_common(1)[0] if topics_list else ('', 0)
            top_journal, top_journal_count = Counter(journals_list).most_common(1)[0] if journals_list else ('', 0)
            
            num_unique_fields = len(set(fields_list))
            num_unique_topics = len(set(topics_list))
            num_unique_journals = len(set(journals_list))
            
            # Affiliation metrics
            all_institutions = set()
            for p in papers_to_date:
                all_institutions.update(p['institutions'])
            
            num_affiliations = len(all_institutions)
            top_affiliation = list(all_institutions)[0] if all_institutions else ''
            
            # Special paper types
            sdl_papers = sum(1 for p in papers_to_date if p['is_sdl'])
            ai_papers = sum(1 for p in papers_to_date if p['is_ai'])
            robotics_papers = sum(1 for p in papers_to_date if p['is_robotics'])
            
            # Create row
            rows.append({
                'author_id': author_id,
                'year': target_year,
                'author_name': author_name,
                'total_papers_to_date': total_papers,
                'first_author_papers_to_date': first_author_papers,
                'last_author_papers_to_date': last_author_papers,
                'corresponding_author_papers_to_date': corresponding_author_papers,
                'total_citations_to_date': int(total_citations),
                'avg_citations_per_paper_to_date': round(avg_citations, 2),
                'top_field_to_date': top_field,
                'top_field_count_to_date': top_field_count,
                'num_unique_fields_to_date': num_unique_fields,
                'top_topic_to_date': top_topic,
                'top_topic_count_to_date': top_topic_count,
                'num_unique_topics_to_date': num_unique_topics,
                'top_journal_to_date': top_journal,
                'top_journal_count_to_date': top_journal_count,
                'num_unique_journals_to_date': num_unique_journals,
                'num_affiliations_to_date': num_affiliations,
                'top_affiliation_to_date': top_affiliation,
                'sdl_papers_to_date': sdl_papers,
                'ai_papers_to_date': ai_papers,
                'robotics_papers_to_date': robotics_papers
            })
    
    print(f"  Processed {authors_processed:,} authors")
    print(f"  Generated {len(rows):,} (author, year) rows")
    
    # ========================================================================
    # PHASE 3: Create DataFrame and save
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("PHASE 3: Creating DataFrame and saving")
    print("=" * 70)
    
    df = pd.DataFrame(rows)
    
    # Sort by author_id and year
    df = df.sort_values(['author_id', 'year']).reset_index(drop=True)
    
    print(f"\nDataset dimensions: {df.shape}")
    print(f"  Unique authors: {df['author_id'].nunique():,}")
    print(f"  Year range: {df['year'].min()} - {df['year'].max()}")
    print(f"  Avg years per author: {len(df) / df['author_id'].nunique():.2f}")
    
    # Display column information
    print(f"\n📋 Columns in dataset ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        print(f"   {i:2}. {col}")
    
    # Sample data
    print(f"\nSample data (first author's timeline):")
    sample_author = df['author_id'].iloc[0]
    print(df[df['author_id'] == sample_author][['author_id', 'year', 'total_papers_to_date', 
                                                   'total_citations_to_date', 'top_field_to_date']].to_string(index=False))
    
    # Save to CSV
    print(f"\n💾 Saving to: {output_csv}")
    df.to_csv(output_csv, index=False)
    
    print(f"\n{'='*70}")
    print("✅ YEARLY AUTHOR DATASET CREATED SUCCESSFULLY!")
    print("=" * 70)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return df


if __name__ == "__main__":
    df = build_author_yearly_dataset(years)
