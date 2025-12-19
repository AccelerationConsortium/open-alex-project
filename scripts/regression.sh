#!/bin/bash
#SBATCH --job-name=cs_experience_regression
#SBATCH --account=def-kmcel                  
#SBATCH --time=2:00:00                      
#SBATCH --mem=128G                           
#SBATCH --cpus-per-task=1      
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "CS Experience Regressions"
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
cd /project/def-kmcel/hridansh/openalex_project/py_code

# Print Python info
echo ""
echo "Python environment:"
python --version
echo ""

# Run the regression dataset creation
time python cs_experience_regression.py

echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="
