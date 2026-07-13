# Table of Contents

1. [Tech Stack](#tech-stack)
2. [Data Retrieval from Open Alex API 2012-2025](#data-retrieval-from-open-alex-api-2012---2025)
3. [Classifying Papers as SDL](#classifying-papers-as-sdl)
4. [Classifying AI Robotics Papers](#tech-stack)
5. [Graphing Team Size Comparison: SDL v Non SDL](#graphing-team-size-comparison-sdl-v-non-sdl)
6. [Creating an Author Dataset](#creating-an-author-dataset)
7. [Creating a Regression Dataset](#creating-a-regression-dataset)
8. [Running Regression Models](#running-regression-models)



# Tech Stack

- Python 
- Python packages: `requests`, `pandas`, `json`,  `os`, `numpy`, `mathplotlib`, `pyarrow`, `collections`, `statsmodels`

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

# Creating an Author Dataset 

This section of code reshapes the existing per field dataset to create a author centric dataset. This creates a dataset of all authors and aggregates career-level metrics, such as total papers, citation counts, and experience with SDL, AI, and Robotics research.

 **Note:** A separate Exploratory Data Analysis (EDA) (named author_metrics_eda.txt) file is available for a detailed explanation of all columns within this dataset.

## Code Explanation

The script processes all papers in our dataset to create the author level dataset. It does it in two phases:

1.  **Phase 1: Accumulation:** The script iterates through the TSV files and extracts all author related information from each paper. It accumulates this raw data into temporary dictionary structures in memory for each author across all the papers they are authors of in any capacity.
2.  **Phase 2: Aggregation:** After all papers are processed, the script aggregates the accumulated raw data. It calculates final metrics like the total citation sum, average citations per paper, and determines the author's top field, top topic, and top journal based on frequency counts.


## Running the Script 

### Before Running

1.  **Dependencies:** Ensure the **`collections`** module is available (this is a standard Python library).

### Execution Command

To run the script, execute the following:

```bash
python author_dataset.py
```

# Creating a Regression Dataset

This section explains how to recreate the filtered dataset containing 490k papers approximately. This is the dataset that was used for various regression models. This dataset is created by consolidating and enriching the complete $\sim 26$ million paper corpus before applying strict filtering criteria.

> **Note:** A separate Exploratory Data Analysis (EDA) (named regression_dataset_subset_eda.txt) file is available for a detailed explanation of all columns, transformations, and data distributions within this regression dataset.

## Code Explanation

The `regression_dataset.py` script first processes all papers across the 4 fields across all years to create an intermediate dataset with the necessary columns for regression analysis. The code does the following:

1.  **Row by Row Data Consolidation** Each row of data in the output file cotains 40+ columns of necessary variables for each paper.
2. **Author Metrics Merge:** Uses the author metrics dataset, to include key author features (such as total papers, citations etc.) in our regression dataset.
3.  **Feature Engineering:**
    * Applies **transformations** (Inverse Hyperbolic Sine ($\text{asinh}$) transformations to variables such as citation counts to normalize them as they are extremely skewed.


## Before Running

1.  **Files needed:** Verify that all files needed to run the code are input with correct paths. Files needed:
    * `author_metrics_file`
    * `fields directory`: Directory with all files for the 4 different fields.

## Running the Script

To generate the full dataset, run:

```bash
python regression_dataset.py
```

## Output Files 

The script generates the following key files:

* `regression_dataset_subset.csv`
    * `Note: This file contains the final, filtered sample of $\sim 490,000$ papers used for the regression instead of the larger 26 million paper dataset. The filtering from 26M to 490k observations is explained in the running regressions section.
* `regression_dataset_subset_eda.txt`
   
# Running Regression Models 

This section executes the main empirical analysis by running two distinct sets of OLS regression models using the final $\sim 490,000$ paper dataset. The goal is to estimate:
1.  The causal effect of whether a research paper is an SDL paper on its **team size**.
2.  The effect of **team size** and **SDL** on the number of **citations** a paper receives.

## Team Size Regression Analysis

This analysis tests whether SDL papers systematically have different team sizes compared to traditional research papers, while controlling for factors such as publishing journals, topics, author level controls etc.

### Code Explanation (`regression_analysis.py`)

The script performs three main steps:
1.  **Conditional Filtering:** Loads the regression dataset and filters it to create the final analytical sample (approx. 490k observations). Papers are retained only if they are published in an SDL journal (any journal which has published one or more of the papers in the SDL databse) or share an SDL primary topic.
2.  **Model Estimation:** Executes 14 distinct OLS models (Baseline, Corresponding Author, and AI/Robotics Subsamples).
3.  **Output Generation:** Saves individual text summaries for each model and a comparative CSV table.

### Regression Equation (Simplified)

All models estimate the effect of SDL on Team Size:

$$\text{Team Size} = \text{Intercept} + \beta_1 (\text{SDL}) + \text{Controls} + \text{Fixed Effects}$$

Where $\beta_1$ represents the difference in team size for SDL papers compared to non-SDL papers.

### Model Descriptions

| Model Group | Models | Description |
| :--- | :--- | :--- |
| **Baseline** | **Models 1–6** | **Model 1:** Simple correlation (Full data vs Matched sample).<br>**Model 2:** Adds **Author Controls** (accounting for author productivity/experience).<br>**Model 3:** Adds **Year Fixed Effects** (time trends).<br>**Model 4:** Adds **Field Fixed Effects**.<br>**Model 5:** Adds **Journal Fixed Effects** (journal norms).<br>**Model 6:** Adds **Topic Fixed Effects** (specific research area norms). |
| **AI/Robotics Subsamples** | **Models 21–26** | Tests the effect specifically within **AI papers** (Model 21), **Robotics papers** (Model 22), and their interaction terms with SDL's. |


## Citation Regression Analysis

This analysis tests whether SDL papers receive more citations and the potential impact team sizes also has on citations.

### Code Explanation (citation_regression_analysis.py)

This script follows a similar structure to the team size analysis but focuses on citations as the outcome:
1.  **Filtering:** Loads the same filtered 490k dataset (matched on Journals/Topics).
2.  **Model Estimation:** Runs 6 regression models, culminating in an interaction model to test if the benefit of larger teams differs for SDL papers.
3.  **Output Generation:** Create and save model summaries and coefficient tables.

### Regression Equation 

These models estimate the effect of Team Size and SDL on Citations:

$$\text{Citations} = \text{Intercept} + \beta_1 (\text{Team Size}) + \beta_2 (\text{SDL}) + \text{Controls} + \text{Fixed Effects}$$

**Model 6** adds an interaction term to test if the team size effect depends on SDL status:

$$\text{Citations} = \dots + \beta_3 (\text{Team Size} \times \text{SDL}) + \dots$$

### Model Descriptions

| Model | Added Features | Purpose |
| :--- | :--- | :--- |
| **Model 1** | Team Size Only | Baseline test: Regression of Citations on Team Size. |
| **Model 2** | + SDL Indicator | Adds the binary SDL variable to test if SDL papers get more citations. |
| **Model 3** | + Author Controls | Adds controls for authors such as last/first author citations and papers. |
| **Model 4** | + Topic FE | Adds Fixed Effects for Primary Topic Name. |
| **Model 5** | + Journal FE | Adds Fixed Effects for Journal Name. |
| **Model 6** | + Interaction | Adds an interaction term ($\text{Team Size} \times \text{SDL}$) to test if SDL papers benefit differently from larger teams. |

## Running the Scripts 

### Before Running (either script)

1.  **Dependencies:** Ensure the `statsmodels` package is installed.
2.  **Files Needed:** Both scripts (`regression_analysis.py` and `citation_regression_analysis.py`) require the same inputs. Ensure all input files present and their path is set correctly:
    * `FULL_DATA`: The regression dataset (`regression_dataset.csv`).
    * `SDL_JOURNALS_FILE`: List of journal names where SDL papers have been published.
    * `SDL_PRIMARY_TOPICS_FILE`: List of primary topics for all papers in the Tom. et al SDL database.

### Execution Commands

**To run the Team Size Analysis:**
```bash
python regression_analysis.py
```
**To run the Citation Analysis:**
```bash
python citation_regression_analysis.py
```