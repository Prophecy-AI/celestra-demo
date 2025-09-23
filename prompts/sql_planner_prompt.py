class SQLPlannerPrompt:
    def __init__(self):
        pass

    def generate_sql(self, query: str) -> str:
        # Placeholder for SQL generation
        # This would typically use the complete_prompt or a dedicated SQL prompt
        from prompts.complete_prompt import build_complete_sql_prompt
        import os
        # import anthropic

        system_prompt = build_complete_sql_prompt(
            med_table=os.getenv("MED_TABLE", "unique-bonbon-472921-q8.Claims.medical_claims"),
            rx_table=os.getenv("RX_TABLE", "unique-bonbon-472921-q8.Claims.rx_claims"),
        )

        # anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        # response = anthropic_client.messages.create(
        #     model="claude-3-5-sonnet-20241022",
        #     max_tokens=4096,
        #     system=system_prompt,
        #     messages=[
        #         {"role": "user", "content": query}
        #     ]
        # )
        # return response.content[0].text

        # For now, return a placeholder
        return f"-- SQL for: {query}\nSELECT 'placeholder' as result;"