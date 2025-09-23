import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROVIDERS_DATA_DICTIONARY = """
PROVIDERS CSV COLUMNS:
- docnexus_url: URL to provider profile
- type_1_npi: Unique provider NPI identifier (e.g., "1033439047")
- type_2_npi_names: JSON array of organization names
- type_2_npis: JSON array of organization NPI numbers
- first_name: Provider first name (e.g., "ANDREW")
- middle_name: Provider middle name (e.g., "JAMES")
- last_name: Provider last name (e.g., "GROSSBACH")
- gender: Provider gender (M/F)
- specialties: JSON array of medical specialties (e.g., ["NEUROLOGICAL SURGERY"])
- conditions_tags: JSON array of condition tags with expertise levels
- conditions: JSON array of medical conditions provider treats
- cities: JSON array of cities where provider practices
- states: JSON array of states where provider practices
- counties: JSON array of counties where provider practices
- city_states: JSON array of city, state combinations
- hospital_names: JSON array of hospital affiliations
- system_names: JSON array of health system affiliations
- affiliations: JSON array of other affiliations
- best_type_2_npi: Primary organization NPI
- best_hospital_name: Primary hospital affiliation
- best_system_name: Primary health system
- phone: Contact phone number
- email: Contact email address
- linkedin: LinkedIn profile URL
- twitter: Twitter handle/URL
- has_youtube: Boolean for YouTube presence
- has_podcast: Boolean for podcast presence
- has_linkedin: Boolean for LinkedIn presence
- has_twitter: Boolean for Twitter presence
- num_payments: Number of reported payments
- num_clinical_trials: Number of clinical trials
- num_publications: Number of publications
- org_type: Type of organization
"""

CLAIMS_DATA_DICTIONARY = """
MOUNJARO CLAIM SAMPLE CSV COLUMNS:
- RX_ANCHOR_DD: Prescription anchor date
- RX_CLAIM_NBR: Claim number identifier
- PATIENT_ID: Patient identifier
- SERVICE_DATE_DD: Date of service
- DATE_PRESCRIPTION_WRITTEN_DD: Date prescription was written
- TRANSACTION_DT: Transaction timestamp
- DISPENSE_NBR: Dispensing number
- TRANSACTION_STATUS_NM: Transaction status (e.g., "Dispensed", "Reject")
- FINAL_STATUS_CD: Final status code
- ADMIN_SERVICE_LINE: Administrative service line
- ADMIN_SUBSERVICE_LINE: Administrative subservice line
- CLINICAL_SERVICE_LINE: Clinical service line
- CLINICAL_SUBSERVICE_LINE: Clinical subservice line
- REJECT_REASON_1_CD: Primary reject reason code
- REJECT_REASON_1_DESC: Primary reject reason description
- REJECT_REASON_2_CD: Secondary reject reason code
- REJECT_REASON_3_CD: Third reject reason code
- REJECT_REASON_4_CD: Fourth reject reason code
- NDC: National Drug Code
- NDC_DESC: Drug description
- NDC_GENERIC_NM: Generic drug name
- NDC_PREFERRED_BRAND_NM: Brand name (e.g., "Mounjaro")
- NDC_IMPLIED_BRAND_NM: Implied brand name
- NDC_DOSAGE_FORM_NM: Dosage form
- NDC_DRUG_FORM_NM: Drug form
- NDC_DRUG_NM: Drug name
- NDC_DRUG_BASE_NM: Base drug name
- NDC_DRUG_SUBCLASS_NM: Drug subclass
- NDC_DRUG_CLASS_NM: Drug class
- NDC_DRUG_GROUP_NM: Drug group
- NDC_ISBRANDED_IND: Branded indicator
- NDC_OTC_INDICATOR_DESC: Over-the-counter indicator
- ROA: Route of administration
- NDC_INGREDIENT_LIST: JSON list of drug ingredients
- PRESCRIBED_NDC: Prescribed NDC code
- DIAGNOSIS_CD: Diagnosis code
- PATIENT_RESIDENCE_CODE_VAL: Patient residence code
- PRESCRIPTION_ORIGIN_CD: Prescription origin code
- DAW_CD: Dispense as written code
- UNIT_OF_MEASUREMENT_CD: Unit of measurement
- BASIS_OF_COST_DETERMINATION_CD: Cost determination basis
- BASIS_OF_REIMBURSEMENT_DETERMINATION_CD: Reimbursement determination basis
- PRIOR_AUTHORIZATION_TYPE_CD: Prior authorization type
- SUBMISSION_CLARIFICATION_CD: Submission clarification
- PHARMACY_NPI_NBR: Pharmacy NPI number
- PHARMACY_NPI_NM: Pharmacy name
- PHARMACY_NPI_ENTITY_CD: Pharmacy entity code
- PHARMACY_NPI_STATE_CD: Pharmacy state code
- PHARMACY_NPI_ZIP5_CD: Pharmacy ZIP code
- PRESCRIBER_NBR_QUAL_CD: Prescriber number qualifier
- PRESCRIBER_NPI_NBR: Prescriber NPI number (links to providers)
- PRESCRIBER_NPI_NM: Prescriber name
- PRESCRIBER_NPI_ENTITY_CD: Prescriber entity code
- PRESCRIBER_NPI_HCO_CLASS_OF_TRADE_DESC: Prescriber trade class
- PRESCRIBER_NPI_HCP_SEGMENT_DESC: Prescriber segment
- PRESCRIBER_NPI_STATE_CD: Prescriber state
- PRESCRIBER_NPI_ZIP5_CD: Prescriber ZIP code
- PCP_NPI_NBR: Primary care provider NPI
- PCP_NPI_NM: Primary care provider name
- PCP_NPI_ENTITY_CD: Primary care provider entity code
- PAYER_ID: Payer identifier
- PAYER_PAYER_NM: Payer name
- PAYER_COB_SEQ_VAL: Coordination of benefits sequence
- PAYER_PLAN_SUBCHANNEL_CD: Plan subchannel code
- PAYER_PLAN_SUBCHANNEL_NM: Plan subchannel name
- PAYER_PLAN_CHANNEL_CD: Plan channel code
- PAYER_PLAN_CHANNEL_NM: Plan channel name
- PAYER_COMPANY_NM: Payer company name
- PAYER_MCO_ISSUER_ID: MCO issuer ID
- PAYER_MCO_ISSUER_NM: MCO issuer name
- PAYER_BIN_NBR: BIN number
- PAYER_PCN_NBR: PCN number
- PAYER_GROUP_STR: Group string
- FILL_NUMBER_VAL: Fill number
- DISPENSED_QUANTITY_VAL: Dispensed quantity
- PRESCRIBED_QUANTITY_VAL: Prescribed quantity
- DAYS_SUPPLY_VAL: Days supply
- NUMBER_OF_REFILLS_AUTHORIZED_VAL: Number of refills authorized
- GROSS_DUE_AMT: Gross due amount
- TOTAL_PAID_AMT: Total paid amount
- PATIENT_TO_PAY_AMT: Patient payment amount
- AWP_UNIT_PRICE_AMT: Average wholesale price per unit
- AWP_CALC_AMT: AWP calculated amount
- UPDATE_TS: Update timestamp
- WAC_UNIT_PRICE_AMT: Wholesale acquisition cost per unit
- WAC_CALC_AMT: WAC calculated amount
"""

SYSTEM_PROMPT = f"""
You are a Python code generator that creates data analysis scripts for two CSV files: providers.csv and Mounjaro Claim Sample.csv.

TASK: Convert natural language queries into executable Python code using pandas.

CRITICAL: Output ONLY the Python code in a code block. No explanations, no descriptions, no text before or after the code.

AVAILABLE DATA:
1. data/providers.csv - Healthcare provider information
2. data/providers_with_embeddings.csv - Providers with semantic embeddings for fuzzy matching
3. data/Mounjaro Claim Sample.csv - Prescription claims data for Mounjaro

KEY RELATIONSHIPS:
- providers.csv 'type_1_npi' links to claims 'PRESCRIBER_NPI_NBR'
- Claims can be filtered by 'NDC_PREFERRED_BRAND_NM' == 'Mounjaro'
- Claims contain prescriber, pharmacy, payer, and drug information

SEMANTIC SEARCH CAPABILITIES:
- Use data/providers_with_embeddings.csv for semantic/fuzzy matching of specialties and conditions
- Available embedding columns: specialties_embedding, conditions_embedding, hospital_names_embedding, system_names_embedding, cities_embedding, states_embedding
- Import semantic functions: from scripts.embeddings import semantic_filter_dataframe
- For semantic queries like "cardiologists", "heart doctors", "diabetes specialists", use semantic_filter_dataframe(df, specialty_terms=['term'], condition_terms=['term'], threshold=0.7)

REQUIREMENTS:
1. Always import pandas as pd
2. Use paths: 'data/providers.csv' and 'data/Mounjaro Claim Sample.csv' (will be replaced with sandbox paths)
3. Create a main function that returns results
4. Include a __main__ section that calls the function and prints results
5. Handle potential data type issues (NPI numbers may be float)
6. Keep code simple and clean
7. Sort results meaningfully when applicable
8. For counting/aggregation queries, use descriptive column names

COMMON PATTERNS:
- Filter claims by drug: df[df['NDC_PREFERRED_BRAND_NM'] == 'Mounjaro']
- Group by prescriber: groupby(['PRESCRIBER_NPI_NBR', 'PRESCRIBER_NPI_NM'])
- Count prescriptions: .size().reset_index(name='prescription_count')
- Join providers and claims: pd.merge(providers, claims, left_on='type_1_npi', right_on='PRESCRIBER_NPI_NBR')
- Filter high-volume: df[df['count_column'] > threshold]
- Semantic specialty search: semantic_filter_dataframe(df, specialty_terms=['cardiology', 'heart'], threshold=0.7)
- Semantic condition search: semantic_filter_dataframe(df, condition_terms=['diabetes', 'blood sugar'], threshold=0.7)
- Combined semantic search: semantic_filter_dataframe(df, specialty_terms=['neurology'], condition_terms=['stroke'], threshold=0.7)

DATA DICTIONARIES:
{PROVIDERS_DATA_DICTIONARY}

{CLAIMS_DATA_DICTIONARY}

OUTPUT FORMAT:
Generate ONLY complete, executable Python code. No explanations, no markdown, no comments outside the code block.

EXAMPLE OUTPUT:
```python
import pandas as pd

def analyze_data():
    # Read data
    df = pd.read_csv('data/Mounjaro Claim Sample.csv')
    
    # Analysis logic here
    result = df.groupby('column').size()
    
    return result

if __name__ == "__main__":
    result = analyze_data()
    print(result)
```
"""

class PlannerPrompt:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def generate_code(self, query: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content

if __name__ == "__main__":
    planner = PlannerPrompt()
    while True:
        user_query = input("Enter your query (or 'quit' to exit): ")
        if user_query.lower() == 'quit':
            break
        
        try:
            code = planner.generate_code(user_query)
            print("\nGenerated Python Code:")
            print("=" * 50)
            print(code)
            print("=" * 50)
        except Exception as e:
            print(f"Error generating code: {e}")
