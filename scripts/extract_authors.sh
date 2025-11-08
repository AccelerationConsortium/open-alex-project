#!/bin/bash
#SBATCH --job-name=sampleExtract_AuthorsAffiliations
#SBATCH --account=def-kmcel                  
#SBATCH --time=4:00:00                      
#SBATCH --mem=128G                           
#SBATCH --cpus-per-task=32                    
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "Extracting All Unique Authors"
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

# Run the author extraction
python extract_authors.py

echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="

# Show generated files
# echo ""
# echo "Generated file:"
# ls -lh ../data/unique_authors.csv
# echo ""
# echo "Total authors extracted:"
# tail -n 1 ../data/unique_authors.csv | wc -l