import os
from databricks.sdk import WorkspaceClient

def ask_genie(space_id: str, question: str) -> str:
    """
    Ask a complex data or analytics question to a specific Databricks Genie Space.
    Use this tool when the user asks a question that requires data analysis, aggregations, or querying data that you don't have direct access to via other tools.
    You must provide the `space_id` of the appropriate Genie Space (use the `list_genies` tool to find it).
    """
    try:
        w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))
    except Exception as e:
        return f"Error connecting to Databricks: {str(e)}"
        
    try:
        response = w.genie.start_conversation_and_wait(
            space_id=space_id,
            content=question
        )
        # Note: Depending on the SDK version, the exact attribute for the text content might vary slightly.
        # Usually it's in the messages or the final message content.
        # Let's try to get the latest message content if available, or just stringify the response.
        
        # The response is a GenieMessage. Its 'content' field is just the user's input.
        # The actual answer is stored in the 'attachments' list, specifically inside a TextAttachment.
        if hasattr(response, 'attachments') and response.attachments:
            text_answers = []
            for att in response.attachments:
                if hasattr(att, 'text') and att.text and hasattr(att.text, 'content'):
                    text_answers.append(att.text.content)
                elif hasattr(att, 'query') and att.query and hasattr(att.query, 'query'):
                    # Optionally include the SQL query it ran for transparency
                    text_answers.append(f"Genie executed this SQL: ```sql\n{att.query.query}\n```")
            
            if text_answers:
                return "\n\n".join(text_answers)
                
        return "Genie processed the request but did not return any textual response or attachments."
             
    except Exception as e:
        return f"Error asking Genie: {str(e)}"