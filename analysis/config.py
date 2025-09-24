# API Configuration
OPENAI_API_KEY = "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"

# BigQuery Configuration
BIGQUERY_PROJECT_ID = "unique-bonbon-472921-q8"
BIGQUERY_DATASET = "Claims"
PHARMACY_TABLE = "rx_claims"
MEDICAL_TABLE = "medical_claims"

# Drug Classifications
COMPETITIVE_DRUGS = {
    "Mounjaro": ["tirzepatide"],
    "Ozempic": ["semaglutide"],
    "Trulicity": ["dulaglutide"],
    "Victoza": ["liraglutide"],
    "Rybelsus": ["semaglutide oral"],
    "Wegovy": ["semaglutide weight loss"],
    "Jardiance": ["empagliflozin"],
    "Farxiga": ["dapagliflozin"]
}

DRUG_CLASSES = {
    "GLP-1/GIP": ["Mounjaro"],
    "GLP-1": ["Ozempic", "Trulicity", "Victoza", "Rybelsus", "Wegovy"],
    "SGLT-2": ["Jardiance", "Farxiga"]
}

# Analysis Parameters
ANALYSIS_PARAMS = {
    "min_prescriptions": 10,
    "confidence_threshold": 0.95,
    "temporal_window_days": 365,
    "feature_importance_threshold": 0.05,
    "max_visualization_points": 1000,
    "top_n_default": 10
}

# Model Settings - Using best available OpenAI model
MODEL_CONFIG = {
    "primary_model": "gpt-4o",  # Best model for code generation
    "temperature": 0.1,  # Lower temperature for more consistent code
    "max_tokens": 3000  # Increased for complex analysis code
}

# Visualization Configuration
VIZ_CONFIG = {
    "output_dir": "images",
    "dpi": 150,
    "figure_size": (14, 8),
    "style": "whitegrid",
    "create_dir": True
}