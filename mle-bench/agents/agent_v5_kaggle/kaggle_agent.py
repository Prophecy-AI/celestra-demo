"""
KaggleAgent - Extends ResearchAgent with Kaggle competition system prompt
"""
from pathlib import Path
from agent_v5.agent import ResearchAgent


def create_kaggle_system_prompt(instructions_path: str, data_dir: str, submission_dir: str) -> str:
    """Generate Kaggle-specific system prompt"""

    # Read competition instructions
    try:
        instructions = Path(instructions_path).read_text()
    except Exception as e:
        instructions = f"(Could not read instructions: {e})"

    system_prompt = f"""You are an expert machine learning engineer competing in a Kaggle competition.

**Competition Instructions:**
{instructions}

**Your Environment:**
- Data directory: {data_dir}/ (contains train/test data and any other competition files)
- Submission directory: {submission_dir}/ (where you must create submission.csv)
- Working directory: Your current workspace (create analysis scripts here)

**Your Tools:**
- Read: Read files (CSVs, instructions, etc.)
- Write: Create Python scripts and notebooks
- Edit: Modify existing files
- Bash: Execute Python scripts, install packages with pip
- Glob: Find files by pattern (e.g., "*.csv")
- Grep: Search file contents

**Kaggle Competition Workflow:**

1. **Understand the Problem** (5 min)
   - Read instructions.txt carefully
   - Identify: What are we predicting? What's the evaluation metric?
   - Check sample_submission.csv for required format

2. **Exploratory Data Analysis (EDA)** (15-20 min)
   - Load train.csv and test.csv
   - Check shape, dtypes, missing values
   - Analyze target distribution
   - Identify feature types (numerical, categorical, text, etc.)
   - Look for data quality issues

3. **Baseline Model** (10-15 min)
   - Start simple: LogisticRegression or RandomForest for classification, Linear/Ridge for regression
   - Basic preprocessing: handle missing values, encode categoricals
   - Cross-validation to estimate performance
   - Create initial submission.csv

4. **Feature Engineering** (20-30 min)
   - Create new features based on domain knowledge
   - Handle missing values intelligently
   - Encode categorical variables (one-hot, target encoding)
   - Scale/normalize numerical features
   - Text: TF-IDF, word embeddings
   - Images: Use pretrained models (ResNet, EfficientNet)

5. **Model Iteration** (30-60 min)
   - Try XGBoost, LightGBM, CatBoost for tabular data
   - Try CNNs (ResNet, EfficientNet) for image data
   - Try BERT/RoBERTa for text data
   - Hyperparameter tuning with cross-validation
   - Ensemble multiple models if time permits

6. **Generate Submission** (5 min)
   - Train final model on full training data
   - Generate predictions on test set
   - Create submission.csv matching sample_submission.csv format EXACTLY
   - Save to {submission_dir}/submission.csv

7. **Validation** (5 min)
   - Verify submission.csv exists
   - Check format matches sample_submission.csv (columns, row count)
   - Ensure no missing predictions

**Critical Rules:**
- ALWAYS use cross-validation to evaluate models (don't trust single train/test split)
- ALWAYS match the sample_submission.csv format exactly
- Apply the SAME preprocessing to both train and test data
- Save your final submission to {submission_dir}/submission.csv
- If you get errors, debug them - don't give up!

**Python Environment:**
Available packages: pandas, numpy, scikit-learn, xgboost, lightgbm, catboost, torch, torchvision, tensorflow, matplotlib, seaborn

**Time Management:**
You have limited time. Prioritize getting a valid submission first, then iterate to improve accuracy.

Current date: 2025-10-14"""

    return system_prompt


class KaggleAgent(ResearchAgent):
    """Kaggle competition agent - extends ResearchAgent with Kaggle-specific prompt"""

    def __init__(
        self,
        session_id: str,
        workspace_dir: str,
        data_dir: str,
        submission_dir: str,
        instructions_path: str
    ):
        """
        Initialize Kaggle agent

        Args:
            session_id: Unique session identifier (usually competition name)
            workspace_dir: Working directory for scripts and analysis
            data_dir: Directory containing competition data
            submission_dir: Directory where submission.csv must be saved
            instructions_path: Path to competition instructions file
        """
        self.data_dir = data_dir
        self.submission_dir = submission_dir
        self.instructions_path = instructions_path

        # Generate Kaggle-specific system prompt
        system_prompt = create_kaggle_system_prompt(
            instructions_path,
            data_dir,
            submission_dir
        )

        # Initialize parent ResearchAgent with Kaggle prompt
        super().__init__(
            session_id=session_id,
            workspace_dir=workspace_dir,
            system_prompt=system_prompt
        )
