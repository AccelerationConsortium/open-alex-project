#!/bin/bash
#SBATCH --job-name=s1234
#SBATCH --account=def-kmcel                  
#SBATCH --time=01:00:00                      
#SBATCH --mem=256G                           
#SBATCH --cpus-per-task=1
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "Creating Regression Dataset"
echo "Started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Running on node: $(hostname)"
echo "=========================================="

# Load Python and activate environment
module load python/3.11
source ~/openalex_env/bin/activate

# module load python/3.10.13
# source ~/venvs/regression_env/bin/activate
# Navigate to project directory 
cd /project/def-kmcel/hridansh/openalex_project/py_files

# Print Python info
echo ""
echo "Python environment:"
python --version
echo ""

# Run the regression dataset creation
time python scibert_analysis.py
    
echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="

# # Show generated file
# echo ""
# echo "Generated file:"
# ls -lh regression_dataset.csv
# echo ""
# echo "Total papers in dataset:"
# wc -l regression_dataset.csv