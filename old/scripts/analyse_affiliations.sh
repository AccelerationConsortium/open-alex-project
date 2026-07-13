#!/bin/bash
#SBATCH --job-name=extract_affiliations_EDA
#SBATCH --account=def-kmcel
#SBATCH --time=01:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=2
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "Extracting Author Affiliations"
echo "Started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "=========================================="

# Load Python and activate environment
module load python/3.11
source ~/openalex_env/bin/activate

# Navigate to project directory
cd /project/def-kmcel/hridansh/openalex_project/z_analysis_code

# Run the affiliation extraction
python analyse_affiliations.py

echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="