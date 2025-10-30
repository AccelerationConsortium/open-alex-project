#!/bin/bash
#SBATCH --job-name=Engineering_Extraction_2020
#SBATCH --account=def-kmcel                  
#SBATCH --time=06:30:00                      
#SBATCH --mem=32G                           
#SBATCH --cpus-per-task=2                    
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "Engineering Extraction"
echo "Started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Running on node: $(hostname)"
echo "=========================================="

# Load Python and activate environment
module load python/3.11
source ~/openalex_env/bin/activate

# Navigate to project directory
cd /project/def-kmcel/hridansh/openalex_project

# Print Python info
echo ""
echo "Python environment:"
python --version
echo ""

# Run the analysis - ALL OUTPUT GOES TO LOG FILE
python extracting_files.py

echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="

# Show generated files
echo ""
echo "Generated files:"
ls -lh data/engineering_redownload/
