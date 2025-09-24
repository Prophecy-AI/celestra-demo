import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json
import openai
from config import OPENAI_API_KEY, MODEL_CONFIG

openai.api_key = OPENAI_API_KEY


class QueryAnalyzer:
    """Uses LLM to generate appropriate analysis code for each query"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    def generate_analysis_code(self, query: str, available_columns: List[str], 
                               sample_data: pd.DataFrame) -> str:
        """Generate custom analysis code for the specific query"""
        
        # Create context about available data
        data_context = f"""
        Available columns: {available_columns}
        Sample data shape: {sample_data.shape}
        Data types: {sample_data.dtypes.to_dict()}
        Sample records: {sample_data.head(3).to_dict()}
        """
        
        prompt = f"""
        Generate sophisticated Python code for pharmaceutical market research analysis.
        
        Query: "{query}"
        
        Data Context:
        {data_context}
        
        Requirements for generated code:
        1. Use advanced statistical methods appropriate for pharmaceutical data:
           - Chi-square tests for categorical comparisons
           - T-tests or Mann-Whitney U for continuous variables
           - ANOVA for multi-group comparisons
           - Regression analysis where appropriate
           - Time series analysis for trends
        
        2. Calculate comprehensive metrics:
           - Market share and growth rates
           - Prescriber behavior patterns
           - Patient adherence and persistence
           - Geographic variations
           - Specialty-specific analyses
        
        3. Include proper statistical validation:
           - P-values with appropriate tests
           - Effect sizes (Cohen's d, odds ratios)
           - Confidence intervals
           - Multiple comparison corrections if needed
        
        4. Structure results dictionary with:
           - 'results': Main findings with specific numbers
           - 'statistics': All statistical tests performed with p-values
           - 'interpretation': Clear explanation of findings
           - 'methodology': Description of analysis approach
           - 'key_metrics': Important numerical findings
           - 'comparisons': Any comparative analyses
        
        5. Handle data quality:
           - Remove outliers appropriately
           - Handle missing values
           - Validate sample sizes
        
        The code assumes 'df' is a pandas DataFrame with the data.
        Import any needed libraries (scipy.stats, sklearn, etc).
        Return ONLY executable Python code.
        """
        
        response = self.client.chat.completions.create(
            model=MODEL_CONFIG["primary_model"],
            messages=[
                {"role": "system", "content": "You are an expert pharmaceutical data scientist with deep knowledge of clinical trials, real-world evidence, and market research. Generate sophisticated statistical analysis code that would meet FDA and publication standards."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=3000  # Increased for comprehensive analysis
        )
        
        code = response.choices[0].message.content
        # Clean the code
        code = code.replace('```python', '').replace('```', '').strip()
        
        return code
    
    def execute_analysis(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """Generate and execute custom analysis code"""
        
        try:
            # Generate analysis code
            analysis_code = self.generate_analysis_code(
                query=query,
                available_columns=df.columns.tolist(),
                sample_data=df.sample(min(10, len(df)))
            )
            
            # Create execution namespace
            namespace = {
                'df': df,
                'pd': pd,
                'np': np,
                'scipy': __import__('scipy'),
                'stats': __import__('scipy.stats'),
                'sklearn': __import__('sklearn')
            }
            
            # Execute the generated code
            exec(analysis_code, namespace)
            
            # Extract results (the code should create a 'results' variable)
            if 'results' in namespace:
                return namespace['results']
            elif 'analysis_results' in namespace:
                return namespace['analysis_results']
            else:
                # Try to extract any dict-like result
                for key, value in namespace.items():
                    if isinstance(value, dict) and key not in ['df', 'pd', 'np', 'scipy', 'stats', 'sklearn']:
                        return value
            
            return {
                'error': 'Generated code did not produce expected results',
                'generated_code': analysis_code
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'generated_code': analysis_code if 'analysis_code' in locals() else None
            }
    
    def generate_visualization_code(self, query: str, analysis_results: Dict[str, Any]) -> str:
        """Generate visualization code based on query and results"""
        
        prompt = f"""
        Generate sophisticated visualization code for pharmaceutical market research presentation.
        
        Query: "{query}"
        Analysis results: {list(analysis_results.keys())}
        Key metrics available: {[k for k in analysis_results.keys() if 'metric' in k.lower() or 'share' in k.lower() or 'rate' in k.lower()][:10]}
        
        Requirements:
        1. Create multi-panel figure (2x2 or 2x3 subplots) with comprehensive visualizations
        2. MUST include heatmap for any correlation/comparison data
        3. Use professional pharmaceutical color schemes:
           - Sequential: 'Blues', 'Greens' for positive metrics
           - Diverging: 'RdBu', 'coolwarm' for comparisons
           - Categorical: 'Set2', 'tab10' for different drugs/specialties
        4. Add statistical annotations:
           - P-values on comparisons
           - Percentages on market share
           - Confidence intervals where available
        5. Professional formatting:
           - Clear titles describing the insight
           - Labeled axes with units
           - Legends positioned appropriately
           - Grid for readability
        6. Save to provided 'filename' variable
        
        Available variables: results (dict), plt, sns, pd, np, filename
        Import any needed modules.
        Return ONLY executable Python code.
        """
        
        response = self.client.chat.completions.create(
            model=MODEL_CONFIG["primary_model"],
            messages=[
                {"role": "system", "content": "You are a pharmaceutical data visualization expert who creates publication-quality figures for market research presentations and scientific journals. Your visualizations must clearly communicate statistical findings and business insights."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        
        code = response.choices[0].message.content
        return code.replace('```python', '').replace('```', '').strip()
