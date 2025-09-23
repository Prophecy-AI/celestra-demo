import os
import sys
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from google.cloud import bigquery
from openai import OpenAI
from prompts.rx_claims_prompt import SYSTEM_PROMPT

load_dotenv()

class RXClaimsAgent:
    def __init__(self):
        self.bq_client = bigquery.Client(project="unique-bonbon-472921-q8")
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def execute_sql_query(self, sql: str):
        clean_sql = sql.strip()
        if clean_sql.startswith("```sql"):
            clean_sql = clean_sql[6:]
        if clean_sql.startswith("```"):
            clean_sql = clean_sql[3:]
        if clean_sql.endswith("```"):
            clean_sql = clean_sql[:-3]
            
        query_job = self.bq_client.query(clean_sql)
        results = query_job.result()
        df = results.to_dataframe()
        
        return df
    
    def generate_sql(self, query: str) -> str:
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ],
        )
        return response.choices[0].message.content
    
    def get_data(self, query: str, save_output: bool = False):
        generated_sql = ""
        result_df = None
        error_msg = ""
        
        try:
            generated_sql = self.generate_sql(query)
            result_df = self.execute_sql_query(generated_sql)
        except Exception as e:
            error_msg = f"Error fetching RX claims data: {str(e)}"
            import pandas as pd
            result_df = pd.DataFrame()
        
        if save_output:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"output/rx_claims_query_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write(f"RX Claims Query: {query}\n")
                f.write("=" * 60 + "\n\n")
                f.write("Generated SQL:\n")
                f.write("-" * 40 + "\n")
                f.write(generated_sql + "\n")
                f.write("-" * 40 + "\n\n")
                f.write("Results:\n")
                f.write("-" * 40 + "\n")
                if error_msg:
                    f.write(error_msg + "\n\n")
                elif result_df.empty:
                    f.write("No results found\n\n")
                else:
                    f.write(f"Found {len(result_df)} rows\n\n{result_df.to_string(index=False)}\n\n")
                f.write(f"Timestamp: {timestamp}\n")
            
            print(f"Results saved to {filename}")
        
        if error_msg:
            return error_msg
        return result_df

def main():
    agent = RXClaimsAgent()
    print("RX Claims Agent - Enter queries to test data fetching")
    
    while True:
        try:
            user_input = input("\nRX Query: ").strip()
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
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
