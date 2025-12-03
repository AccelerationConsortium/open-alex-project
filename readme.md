# Table of Contents

1. [Tech Stack](#tech-stack)
2. [Data Retrieval from Open Alex API 2012-2025](#data-retrieval-from-open-alex-api-2012---2025)
3. [Classifying Papers as SDL](#classifying-papers-as-sdl)
4. [Classifying AI Robotics Papers](#tech-stack)
5. [Graphing Team Size Comparison: SDL v Non SDL](#graphing-team-size-comparison-sdl-v-non-sdl)
6. [Creating a Regression Dataset](#creating-a-regression-dataset)



# Tech Stack

- Python 
- Python packages: `requests`, `pandas`, `json`,  `os`, `numpy`, `mathplotlib`

# Data Retrieval from Open Alex API 2012 - 2025

This section of the readme explains how to extract research articles from OpenAlex and store them in TSV (tab-separated values) files. Python is used to connect to the OpenAlex API and save data locally.

## Creating Output Directory

Create a output folder in your main directory to store the files:
```bash
mkdir -p data/material_science  (#create folders for each field)
```

## Extracting Data

To extract data from OpenAlex and save to TSV files, run:
```bash
python extracting_files.py
```

### Before Running

Before running the script, make the following changes:

1. **Update email:**
Enter your email for the API call (required by OpenAlex):
```python
EMAIL = "abc@gmail.com"  
```

2. **Set output directory:**
Specify where TSV files should be saved:
```python
OUTPUT_DIR = "data/material_science"
```

3. **Modify API parameters:**
Ensure API parameters are correct for your field:

- `publication_year:YYYY-YYYY` - Range of years to retrieve
- `primary_topic.field.id:fields/25` - Materials science field ID
  - Use `fields/22` for Engineering
  - Use `fields/17` for Chemistry

### Output

The script will create one TSV file per year for that field in the following format:
- `materials_science_2012.tsv`

# Classifying Papers as SDL

This section mentions how papers in the dataset are classified as Self-Driving Laboratory (SDL) papers or not. This is based on matching DOIs of all papers against DOI's from a given SDL database.


## Before Running

Before running the script, make the following changes:

1. **Set input directory:** Specify which field's data to update. (Code needs to be run separately for each field):
```python
output_directory = "data/engineering" 
```

## Running the Script

To classify SDL papers and update the TSV files, run:
```bash
python sdl_matching.py
```

## Output

The `SDL` column in the TSV files is updated to `1` for papers that match the SDL database.

# Classifying Papers as AI Robotics

This section explains how to identify and mark papers related to AI or Robotics. Two lists of AI and Robotics keywords were created and these are compared against abstracts from all papers. If a keyword match is found then that paper is classified as AI/Robotics respectively.

## Before Running

Before running the script, make the following changes:

1. **Set output directory:** Specify which field's data to update:
```python
output_directory = "data/engineering"  # Change to match your field
```

2. **Set keywords file:** Specify which keyword set to use:
```python
words_file = "data/keywords/AI_Keywords.csv"  # Or "robotics_Keywords.csv"
```

3. **Set keyword type:** Update to match your chosen keywords:
```python
keyword = 'AI'  # Or 'Robotics'
```


## Running the Script

To classify AI or Robotics papers and update the TSV files, run:
```bash
python classify_keywords.py
```

## Output

Two new columns are added to the TSV files:
- `number_of_AI_words` (or `number_of_Robotics_words`) - count of keyword matches
- `AI_Paper` (or `Robotics_Paper`) - set to `1` if match found

# Graphing Team Size Comparison: SDL v Non SDL

This section explains how to reproduce graph which show a comparison of team sizes (author counts variable) between SDL papers and various comparison groups through different filtering options.

## Graphing Options
The script has 6 different graphs based on different filters for the non SDL data. Uncomment the graph needed  in the `if __name__ == "__main__"` section:

1. Option 1: All Data: Compares SDL papers against all non-SDL papers.

2.  Option 2: Same Journals: Compares SDL papers against non-SDL papers published in the same journals.

3. Option 3: Same Topics: Compares SDL papers against non-SDL papers from the same research topics.
4. Option 4: SDL vs AI Papers: Compares SDL papers against AI papers (excluding any papers that are both SDL and AI).
5.  Option 5: SDL vs Robotics Papers: Compares SDL papers against Robotics papers (excluding any papers that are both SDL and Robotics).
6. Option 6: Same Journals and Topics: Compares SDL papers against non-SDL papers that match both the same journals AND the same topics.
7. Option 7: SDL vs (AI and Robotics) papersL Compares SDL papers against non-SDL papers that are both robotics and AI papers.

## Running the Script

To run the analysis:
```bash
python team_size_analysis.py
```

# Creating a Regression Dataset

