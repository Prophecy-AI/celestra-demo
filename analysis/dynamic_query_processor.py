import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
import openai
from data_loader import DataLoader
from query_analyzer import QueryAnalyzer
from config import OPENAI_API_KEY, MODEL_CONFIG
import matplotlib.pyplot as plt
import seaborn as sns
import os

openai.api_key = OPENAI_API_KEY


class DynamicQueryProcessor:
    """Processes queries by dynamically generating analysis code using LLM"""
    
    def __init__(self):
        self.data_loader = DataLoader()
        self.query_analyzer = QueryAnalyzer()
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Ensure images directory exists
        os.makedirs('images', exist_ok=True)
    
    def process(self, query: str) -> Dict[str, Any]:
        """Process query using dynamic LLM-generated analysis"""
        
        # 1. Understand query intent and data needs
        data_requirements = self._determine_data_requirements(query)
        
        # 2. Load required data
        df = self._load_data(data_requirements)
        
        if df.empty:
            return {'error': 'No data available for analysis'}
        
        # 3. Generate and execute custom analysis code
        analysis_results = self.query_analyzer.execute_analysis(df, query)
        
        # 4. Generate visualizations
        viz_filename = self._generate_visualization(query, analysis_results, df)
        
        # 5. Generate insights
        insights = self._generate_insights(query, analysis_results, len(df))
        
        # 6. Prepare technical data
        technical_data = self._prepare_technical_data(
            data_requirements, 
            analysis_results, 
            len(df)
        )
        
        return {
            'query': query,
            'insights': insights,
            'technical_data': technical_data,
            'visualizations': [viz_filename] if viz_filename else [],
            'results': analysis_results
        }
    
    def _determine_data_requirements(self, query: str) -> Dict[str, Any]:
        """Use LLM to determine what data is needed"""
        
        prompt = f"""
        Analyze this pharmaceutical market research query and determine data requirements:
        Query: "{query}"
        
        Return a JSON object with:
        - datasets: list of needed datasets from [rx_claims, medical_claims, providers_bio, provider_payments]
        - drugs: list of drug names mentioned or implied
        - time_range: if a time period is mentioned, provide start and end dates
        - states: list of states if geographic analysis is needed
        - specialties: list of specialties if mentioned
        - analysis_type: main type of analysis (competitor, trend, hcp, market_access, etc.)
        """
        
        response = self.client.chat.completions.create(
            model=MODEL_CONFIG["primary_model"],
            messages=[
                {"role": "system", "content": "You are a pharmaceutical data analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        try:
            requirements = json.loads(response.choices[0].message.content)
        except:
            # Fallback to basic requirements
            requirements = {
                'datasets': ['rx_claims'],
                'drugs': [],
                'time_range': None,
                'states': [],
                'specialties': [],
                'analysis_type': 'general'
            }
        
        return requirements
    
    def _load_data(self, requirements: Dict[str, Any]) -> pd.DataFrame:
        """Load data based on requirements"""
        
        # Load prescription data - all available records
        df = self.data_loader.load_pharmacy_data(
            drug_filter=requirements.get('drugs'),
            state_filter=requirements.get('states'),
            time_range=requirements.get('time_range'),
            limit=None  # Load all available data
        )
        
        # Add HCP data if needed
        if 'providers_bio' in requirements.get('datasets', []):
            hcp_data = self.data_loader.load_hcp_data()
            if not hcp_data.empty and 'PRESCRIBER_NPI_NBR' in df.columns:
                df = df.merge(hcp_data, left_on='PRESCRIBER_NPI_NBR', 
                            right_on='npi', how='left')
        
        # Add payment data if needed
        if 'provider_payments' in requirements.get('datasets', []):
            payments = self.data_loader.load_provider_payments(
                time_range=requirements.get('time_range')
            )
            if not payments.empty and 'PRESCRIBER_NPI_NBR' in df.columns:
                df = df.merge(payments, left_on='PRESCRIBER_NPI_NBR',
                            right_on='physician_npi', how='left')
        
        return df
    
    def _generate_visualization(self, query: str, results: Dict[str, Any], 
                              df: pd.DataFrame) -> Optional[str]:
        """Generate dynamic visualization using LLM"""
        
        # Create a short query-based filename
        query_words = query.lower().split()[:5]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"images/{'_'.join(query_words)}_{timestamp}.png"
        
        try:
            # Generate visualization code
            viz_code = self.query_analyzer.generate_visualization_code(query, results)
            
            # Execute visualization code
            namespace = {
                'results': results,
                'df': df,
                'pd': pd,
                'np': np,
                'plt': plt,
                'sns': sns,
                'filename': filename
            }
            
            exec(viz_code, namespace)
            
            # Ensure the figure is saved
            if plt.gcf().get_axes():
                plt.savefig(filename, dpi=150, bbox_inches='tight')
                plt.close()
                return filename
            
        except Exception as e:
            # Retry with improved prompt
            try:
                improved_code = self._get_improved_visualization_code(query, results, df)
                exec(improved_code, namespace)
                if plt.gcf().get_axes():
                    plt.savefig(filename, dpi=150, bbox_inches='tight')
                    plt.close()
                    return filename
            except:
                # Final fallback
                self._create_fallback_visualization(results, filename)
                return filename
        
        return filename
    
    def _create_fallback_visualization(self, results: Dict[str, Any], filename: str):
        """Create a simple fallback visualization"""
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Try to visualize any numeric data in results
        numeric_data = {}
        for key, value in results.items():
            if isinstance(value, (int, float)):
                numeric_data[key] = value
            elif isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, (int, float)):
                        numeric_data[f"{key}_{k}"] = v
        
        if numeric_data:
            # Create bar chart
            keys = list(numeric_data.keys())[:10]
            values = [numeric_data[k] for k in keys]
            
            ax.bar(range(len(keys)), values)
            ax.set_xticks(range(len(keys)))
            ax.set_xticklabels(keys, rotation=45, ha='right')
            ax.set_title('Analysis Results')
            
        else:
            # Create text summary
            ax.text(0.5, 0.5, 'Analysis Complete\nSee technical data for details',
                   ha='center', va='center', fontsize=16)
            ax.axis('off')
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
    
    def _generate_insights(self, query: str, results: Dict[str, Any], 
                          data_points: int) -> str:
        """Generate human-readable insights"""
        
        prompt = f"""
        Generate concise insights for pharmaceutical market researchers.
        
        Query: "{query}"
        Analysis results: {json.dumps(results, default=str)[:2000]}
        Data points analyzed: {data_points:,}
        
        Provide:
        1. Key findings (3-5 bullet points)
        2. Statistical significance where relevant
        3. Actionable recommendations
        
        Be specific with numbers and percentages.
        """
        
        response = self.client.chat.completions.create(
            model=MODEL_CONFIG["primary_model"],
            messages=[
                {"role": "system", "content": "You are a pharmaceutical market research expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        return response.choices[0].message.content
    
    def _prepare_technical_data(self, requirements: Dict[str, Any],
                               results: Dict[str, Any], 
                               data_points: int) -> Dict[str, Any]:
        """Prepare comprehensive technical data as proof/evidence for insights"""
        
        technical_data = {
            'data_points_analyzed': data_points,
            'datasets_used': requirements.get('datasets', ['rx_claims']),
            'filters_applied': {
                'drugs': requirements.get('drugs', []),
                'time_range': requirements.get('time_range'),
                'states': requirements.get('states', []),
                'specialties': requirements.get('specialties', [])
            },
            'analysis_type': requirements.get('analysis_type', 'dynamic'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Extract all statistical evidence from results
        technical_data['statistical_evidence'] = {}
        
        # Extract p-values with context
        for key, value in results.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if 'p_value' in str(sub_key).lower():
                        technical_data['statistical_evidence'][f"{key}_{sub_key}"] = {
                            'value': sub_value,
                            'significant': sub_value < 0.05,
                            'interpretation': 'statistically significant' if sub_value < 0.05 else 'not significant'
                        }
            elif 'p_value' in str(key).lower():
                technical_data['statistical_evidence'][key] = {
                    'value': value,
                    'significant': value < 0.05,
                    'interpretation': 'statistically significant' if value < 0.05 else 'not significant'
                }
        
        # Extract key metrics as proof points
        technical_data['key_metrics'] = {}
        for key, value in results.items():
            if isinstance(value, (int, float)):
                technical_data['key_metrics'][key] = value
            elif isinstance(value, dict) and 'mean' in value:
                technical_data['key_metrics'][key] = value
            elif isinstance(value, pd.DataFrame):
                technical_data['key_metrics'][key] = {
                    'shape': value.shape,
                    'summary': value.describe().to_dict() if len(value) > 0 else {}
                }
        
        # Extract methodology details
        if 'methodology' in results:
            technical_data['methodology'] = results['methodology']
        
        # Extract data quality indicators
        technical_data['data_quality'] = {
            'total_records': data_points,
            'completeness': 'complete dataset' if data_points > 10000 else 'limited sample',
            'time_coverage': requirements.get('time_range', 'all available dates'),
            'geographic_coverage': len(requirements.get('states', [])) if requirements.get('states') else 'nationwide'
        }
        
        # Statistical test details
        if 'statistics' in results:
            technical_data['statistical_tests_performed'] = results['statistics']
        
        # Extract correlations and relationships
        if 'correlations' in results:
            technical_data['correlations'] = results['correlations']
        
        # Extract comparisons
        if 'comparisons' in results or 'comparison' in results:
            technical_data['comparative_analysis'] = results.get('comparisons', results.get('comparison', {}))
        
        return technical_data
    
    def _get_improved_visualization_code(self, query: str, results: Dict[str, Any], df: pd.DataFrame) -> str:
        """Generate improved visualization code with heatmaps and comprehensive charts"""
        
        prompt = f"""
        Generate Python code for pharmaceutical market research visualization.
        
        Query: "{query}"
        Results structure: {list(results.keys())}
        Data columns: {df.columns.tolist()[:20]}
        
        Requirements:
        1. Create multi-panel figure with subplots
        2. Include heatmap if correlation/comparison data exists
        3. Use professional color schemes (seaborn)
        4. Add proper titles, labels, and legends
        5. Include statistical annotations (p-values, percentages)
        6. Save to filename variable provided
        
        Code must use: plt, sns, pd, np, results, df, filename
        Generate only executable Python code.
        """
        
        response = self.client.chat.completions.create(
            model=MODEL_CONFIG["primary_model"],
            messages=[
                {"role": "system", "content": "You are a data visualization expert. Generate publication-quality pharmaceutical visualizations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        code = response.choices[0].message.content
        return code.replace('```python', '').replace('```', '').strip()
