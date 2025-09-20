import pandas as pd
import json
import ast
from typing import Dict, List, Any, Optional

class PlanExecutor:
    def __init__(self, csv_path: str = "data/providers.csv"):
        self.df = pd.read_csv(csv_path)
        self._preprocess_data()
    
    def _preprocess_data(self):
        self.df['name'] = self.df['first_name'] + ' ' + self.df['last_name']
        self.df['npi'] = self.df['type_1_npi']
        
        array_columns = ['specialties', 'states', 'hospital_names', 'system_names']
        for col in array_columns:
            if col in self.df.columns:
                self.df[col] = self.df[col].apply(self._parse_array_string)
    
    def _parse_array_string(self, value) -> List[str]:
        if pd.isna(value) or value == '':
            return []
        try:
            if isinstance(value, str):
                return json.loads(value)
            return value if isinstance(value, list) else []
        except:
            return []
    
    def execute_plan(self, plan: Dict[str, Any]) -> pd.DataFrame:
        result_df = self.df.copy()
        
        if plan.get('filters'):
            result_df = self._apply_filters(result_df, plan['filters'])
        
        if plan.get('projection'):
            result_df = self._apply_projection(result_df, plan['projection'])
        
        if plan.get('order_by'):
            result_df = self._apply_ordering(result_df, plan['order_by'])
        
        if plan.get('limit'):
            result_df = result_df.head(plan['limit'])
        
        return result_df
    
    def _apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        result_df = df.copy()
        
        if filters.get('specialty_any'):
            mask = result_df['specialties'].apply(
                lambda x: any(spec.lower() in [s.lower() for s in x] for spec in filters['specialty_any'])
            )
            result_df = result_df[mask]
        
        if filters.get('state_any'):
            mask = result_df['states'].apply(
                lambda x: any(state.lower() in [s.lower() for s in x] for state in filters['state_any'])
            )
            result_df = result_df[mask]
        
        if filters.get('hospital_any'):
            mask = result_df['hospital_names'].apply(
                lambda x: any(hosp.lower() in [h.lower() for h in x] for hosp in filters['hospital_any'])
            )
            result_df = result_df[mask]
        
        if filters.get('system_any'):
            mask = result_df['system_names'].apply(
                lambda x: any(sys.lower() in [s.lower() for s in x] for sys in filters['system_any'])
            )
            result_df = result_df[mask]
        
        if filters.get('org_type_any'):
            mask = result_df['org_type'].apply(
                lambda x: x.lower() in [ot.lower() for ot in filters['org_type_any']] if pd.notna(x) else False
            )
            result_df = result_df[mask]
        
        if filters.get('publications_min') is not None:
            result_df = result_df[result_df['num_publications'] >= filters['publications_min']]
        
        return result_df
    
    def _apply_projection(self, df: pd.DataFrame, projection: List[str]) -> pd.DataFrame:
        available_columns = []
        for col in projection:
            if col in df.columns:
                available_columns.append(col)
        return df[available_columns]
    
    def _apply_ordering(self, df: pd.DataFrame, order_by: List[str]) -> pd.DataFrame:
        sort_columns = []
        sort_ascending = []
        
        for order_spec in order_by:
            parts = order_spec.split()
            column = parts[0]
            direction = parts[1].upper() if len(parts) > 1 else 'ASC'
            
            if column in df.columns:
                sort_columns.append(column)
                sort_ascending.append(direction == 'ASC')
        
        if sort_columns:
            return df.sort_values(by=sort_columns, ascending=sort_ascending)
        return df

def execute_json_plan(json_plan: str, csv_path: str = "data/providers.csv") -> pd.DataFrame:
    plan = json.loads(json_plan)
    executor = PlanExecutor(csv_path)
    return executor.execute_plan(plan)

if __name__ == "__main__":
    sample_plan = """{
        "filters": {
            "specialty_any": null,
            "state_any": null,
            "hospital_any": null,
            "system_any": null,
            "org_type_any": null,
            "publications_min": 30
        },
        "projection": [
            "npi",
            "name",
            "num_publications"
        ],
        "order_by": [
            "num_publications DESC",
            "name ASC"
        ],
        "limit": 20,
        "plan_notes": null
    }"""
    
    result = execute_json_plan(sample_plan)
    print(result.to_string(index=False))
