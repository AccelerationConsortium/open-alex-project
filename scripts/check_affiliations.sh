#!/bin/bash
#SBATCH --job-name=Check_Affiliations_chem
#SBATCH --account=def-kmcel                  
#SBATCH --time=00:30:00                      
#SBATCH --mem=16G                           
#SBATCH --cpus-per-task=1                    
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "Checking Affiliations  Multiple"
echo "Started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Running on node: $(hostname)"
echo "=========================================="

# Load Python and activate environment
module load python/3.11
source ~/openalex_env/bin/activate

# Navigate to project directory
cd /project/def-kmcel/hridansh/openalex_project/test_code

# Print Python info
echo ""
echo "Python environment:"
python --version
echo ""

# Run the affiliation check
python check_affiliations.py

echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="

# Show generated files
echo ""
echo "Generated file:"
