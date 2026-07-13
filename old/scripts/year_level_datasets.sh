#!/bin/bash
#SBATCH --job-name=year_regression_dataset
#SBATCH --account=def-kmcel                  
#SBATCH --time=3:00:00                      
#SBATCH --mem=256G                           
#SBATCH --cpus-per-task=8                 
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "Extracting Regression Dataset Per Year"
echo "Started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Running on node: $(hostname)"
echo "=========================================="

# Load Python and activate environment
module load python/3.11
source ~/openalex_env/bin/activate

# Navigate to project directory
cd /project/def-kmcel/hridansh/openalex_project/py_files

# Print Python info
echo ""
echo "Python environment:"
python --version
echo ""

# Run the author extraction
python year_regression_dataset.py

echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="
