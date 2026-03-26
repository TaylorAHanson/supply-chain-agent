import os
from databricks.sdk import WorkspaceClient

def list_genies() -> str:
    """
    Fetch a list of available Databricks Genie spaces, including their names, descriptions, and space_ids.
    Use this tool to find the appropriate Genie Space ID before calling the `ask_genie` tool.
    """
    try:
        w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE"))
    except Exception as e:
        return f"Error connecting to Databricks: {str(e)}"
        
    try:
        res = w.genie.list_spaces()
        if not res or not hasattr(res, 'spaces') or not res.spaces:
            return "No Genie spaces found."
            
        genies_info = []
        for space in res.spaces:
            name = getattr(space, 'title', 'Unknown Name')
            description = getattr(space, 'description', 'No description provided')
            space_id = getattr(space, 'space_id', 'Unknown ID')
            
            genies_info.append(f"- **Name**: {name}\n  **Space ID**: {space_id}\n  **Description**: {description}")
            
        return "\n\n".join(genies_info)
        
    except Exception as e:
        return f"Error listing Genies: {str(e)}"