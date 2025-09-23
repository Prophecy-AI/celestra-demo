import os
import sys
import time
import polars as pl
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from google.cloud import bigquery
# from openai import OpenAI
import anthropic
from prompts.med_claims_prompt import SYSTEM_PROMPT

load_dotenv()

class MedClaimsAgent:
    def __init__(self):
        self.bq_client = bigquery.Client(project="unique-bonbon-472921-q8")
        self.anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
    def execute_sql_query(self, sql: str):
        clean_sql = sql.strip()
        if clean_sql.startswith("```sql"):
            clean_sql = clean_sql[6:]
        if clean_sql.startswith("```"):
            clean_sql = clean_sql[3:]
        if clean_sql.endswith("```"):
            clean_sql = clean_sql[:-3]
        print(clean_sql)
        query_job = self.bq_client.query(clean_sql)
        results = query_job.result()
        # Convert BigQuery result to Arrow then to Polars
        arrow_table = results.to_arrow()
        df = pl.from_arrow(arrow_table)

        return df
    
    def generate_sql(self, query: str) -> str:
        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": query}
            ]
        )
        print(response.content[0].text)
        return response.content[0].text
    
    def get_data(self, query: str, save_output: bool = False):
        generated_sql = ""
        result_df = None
        error_msg = ""
        

        generated_sql = self.generate_sql(query)
        result_df = self.execute_sql_query(generated_sql)
        
        if save_output:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"output/med_claims_query_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write(f"Medical Claims Query: {query}\n")
                f.write("=" * 60 + "\n\n")
                f.write("Generated SQL:\n")
                f.write("-" * 40 + "\n")
                f.write(generated_sql + "\n")
                f.write("-" * 40 + "\n\n")
                f.write("Results:\n")
                f.write("-" * 40 + "\n")
                if error_msg:
                    f.write(error_msg + "\n\n")
                elif result_df.is_empty():
                    f.write("No results found\n\n")
                else:
                    f.write(f"Found {len(result_df)} rows\n\n{str(result_df)}\n\n")
                f.write(f"Timestamp: {timestamp}\n")
            
            print(f"Results saved to {filename}")
        
        if error_msg:
            return error_msg
        return result_df

def main():
    agent = MedClaimsAgent()
    print("Medical Claims Agent - Enter queries to test data fetching")
    
    while True:
        try:
            user_input = input("\nMed Query: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
                
            result = agent.get_data(user_input)
            print(f"\nResult: {result}")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
    

if __name__ == "__main__":
    main()
