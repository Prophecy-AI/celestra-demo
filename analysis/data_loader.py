import pandas as pd
import numpy as np
from typing import Optional, List, Tuple
from datetime import datetime
from google.cloud import bigquery
from config import *


class DataLoader:
    def __init__(self):
        self.client = bigquery.Client(project=BIGQUERY_PROJECT_ID)
        print(f"Connected to BigQuery: {BIGQUERY_PROJECT_ID}")
        
    def load_pharmacy_data(self, 
                          drug_filter: Optional[List[str]] = None, 
                          state_filter: Optional[List[str]] = None,
                          time_range: Optional[Tuple[str, str]] = None,
                          limit: Optional[int] = None) -> pd.DataFrame:
        query = f"""
        SELECT 
            PRESCRIBER_NPI_NBR,
            PRESCRIBER_NPI_NM,
            PRESCRIBER_NPI_HCP_SEGMENT_DESC,
            PRESCRIBER_NPI_STATE_CD,
            PRESCRIBER_NPI_ZIP5_CD,
            RX_ANCHOR_DD,
            SERVICE_DATE_DD,
            NDC,
            NDC_PREFERRED_BRAND_NM,
            NDC_DRUG_CLASS_NM,
            NDC_DRUG_SUBCLASS_NM,
            PHARMACY_NPI_STATE_CD,
            PAYER_PLAN_CHANNEL_NM,
            DISPENSED_QUANTITY_VAL,
            DAYS_SUPPLY_VAL,
            TOTAL_PAID_AMT,
            PATIENT_TO_PAY_AMT,
            EXTRACT(YEAR FROM RX_ANCHOR_DD) as rx_year,
            COUNT(*) as claim_count,
            1 as patient_count
        FROM `{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET}.{PHARMACY_TABLE}`
        WHERE 1=1
        """
        
        # Add time range filter
        if time_range:
            query += f" AND RX_ANCHOR_DD BETWEEN '{time_range[0]}' AND '{time_range[1]}'"
        
        if drug_filter:
            drug_list = "','".join(drug_filter)
            query += f" AND NDC_PREFERRED_BRAND_NM IN ('{drug_list}')"
            
        if state_filter:
            state_list = "','".join(state_filter)
            query += f" AND PRESCRIBER_NPI_STATE_CD IN ('{state_list}')"
        
        query += """
        GROUP BY 
            PRESCRIBER_NPI_NBR, PRESCRIBER_NPI_NM, PRESCRIBER_NPI_HCP_SEGMENT_DESC,
            PRESCRIBER_NPI_STATE_CD, PRESCRIBER_NPI_ZIP5_CD, RX_ANCHOR_DD,
            SERVICE_DATE_DD, NDC, NDC_PREFERRED_BRAND_NM, NDC_DRUG_CLASS_NM,
            NDC_DRUG_SUBCLASS_NM, PHARMACY_NPI_STATE_CD, PAYER_PLAN_CHANNEL_NM,
            DISPENSED_QUANTITY_VAL, DAYS_SUPPLY_VAL, TOTAL_PAID_AMT, PATIENT_TO_PAY_AMT
        """
        
        if limit:
            query += f" LIMIT {limit}"
        # No limit means load all available data
            
        return self.client.query(query).to_dataframe()
    
    def load_competitive_landscape(self, 
                                  target_drug: str,
                                  time_range: Optional[Tuple[str, str]] = None,
                                  include_all_competitors: bool = True) -> pd.DataFrame:
        competitor_drugs = [target_drug]
        
        if include_all_competitors:
            for drug_class, drugs in DRUG_CLASSES.items():
                if target_drug in drugs:
                    competitor_drugs = drugs
                    break
        
        df = self.load_pharmacy_data(
            drug_filter=competitor_drugs,
            time_range=time_range
        )
        df['is_target_drug'] = df['NDC_PREFERRED_BRAND_NM'] == target_drug
        df['market_share'] = df.groupby('NDC_PREFERRED_BRAND_NM')['claim_count'].transform(
            lambda x: x / df['claim_count'].sum()
        )
        
        return df
    
    def get_data_summary(self, time_range: Optional[Tuple[str, str]] = None) -> dict:
        query = f"""
        SELECT 
            COUNT(DISTINCT PRESCRIBER_NPI_NBR) as total_prescribers,
            COUNT(DISTINCT NDC) as total_ndcs,
            COUNT(DISTINCT NDC_PREFERRED_BRAND_NM) as total_brands,
            COUNT(DISTINCT PRESCRIBER_NPI_STATE_CD) as total_states,
            COUNT(*) as total_claims,
            MIN(RX_ANCHOR_DD) as earliest_date,
            MAX(RX_ANCHOR_DD) as latest_date,
            SUM(TOTAL_PAID_AMT) as total_paid_amount
        FROM `{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET}.{PHARMACY_TABLE}`
        WHERE 1=1
        """
        
        if time_range:
            query += f" AND RX_ANCHOR_DD BETWEEN '{time_range[0]}' AND '{time_range[1]}'"
        
        result = self.client.query(query).to_dataframe().iloc[0].to_dict()
        
        period_str = f" ({time_range[0]} to {time_range[1]})" if time_range else ""
        
        return {
            'prescribers': f"{result['total_prescribers']:,}",
            'drugs': f"{result['total_brands']:,}",
            'states': result['total_states'],
            'claims': f"{result['total_claims']:,}",
            'date_range': f"{result['earliest_date']} to {result['latest_date']}{period_str}",
            'total_value': f"${result['total_paid_amount']:,.2f}"
        }
    
    def get_top_drugs(self, n: int = 10, time_range: Optional[Tuple[str, str]] = None) -> pd.DataFrame:
        query = f"""
        SELECT 
            NDC_PREFERRED_BRAND_NM as drug_name,
            COUNT(*) as prescription_count,
            SUM(TOTAL_PAID_AMT) as total_value,
            COUNT(DISTINCT PRESCRIBER_NPI_NBR) as prescriber_count,
            AVG(DAYS_SUPPLY_VAL) as avg_days_supply
        FROM `{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET}.{PHARMACY_TABLE}`
        WHERE 1=1
        """
        
        if time_range:
            query += f" AND RX_ANCHOR_DD BETWEEN '{time_range[0]}' AND '{time_range[1]}'"
        
        query += f"""
        GROUP BY NDC_PREFERRED_BRAND_NM
        ORDER BY prescription_count DESC
        LIMIT {n}
        """
        
        return self.client.query(query).to_dataframe()
    
    def load_hcp_data(self, time_range: Optional[Tuple[str, str]] = None) -> pd.DataFrame:
        query = f"""
        SELECT *
        FROM `{BIGQUERY_PROJECT_ID}.HCP.providers_bio`
        LIMIT 10000
        """
        return self.client.query(query).to_dataframe()
    
    def load_provider_payments(self, time_range: Optional[Tuple[str, str]] = None) -> pd.DataFrame:
        query = f"""
        SELECT *
        FROM `{BIGQUERY_PROJECT_ID}.HCP.provider_payments`
        WHERE 1=1
        """
        
        # If time range specified, filter by program_year
        if time_range:
            start_year = datetime.strptime(time_range[0], '%Y-%m-%d').year
            end_year = datetime.strptime(time_range[1], '%Y-%m-%d').year
            query += f" AND program_year BETWEEN {start_year} AND {end_year}"
        
        query += " LIMIT 10000"
        return self.client.query(query).to_dataframe()
    
    def load_doctors_npi(self) -> pd.DataFrame:
        query = f"""
        SELECT *
        FROM `{BIGQUERY_PROJECT_ID}.Doctors.us_npi_doctors`
        LIMIT 10000
        """
        return self.client.query(query).to_dataframe()