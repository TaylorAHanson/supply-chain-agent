import os

def read_skill(skill_name: str) -> str:
    """
    Reads the contents of a specific skill document. Use this to read the instructions for a given skill.
    IMPORTANT: DO NOT output the raw content of the skill file into the chat window. Read it silently and follow the instructions.
    
    :param skill_name: The name of the skill to read (e.g., 'analyze_safety_stock').
    """
    import os
    from backend.agent.config import SKILLS_VOLUME_PATH, DATABRICKS_WAREHOUSE_ID
    from databricks.sdk import WorkspaceClient
    
    try:
        is_app = bool(os.environ.get("DATABRICKS_APP_NAME"))
        
        if is_app:
            w = WorkspaceClient()
        else:
            profile = os.getenv("DATABRICKS_PROFILE", "myenv")
            w = WorkspaceClient(profile=profile)
            
        # Query for skills (volumes named 'skills') to find where this skill lives
        query_skills = """
        SELECT volume_catalog, volume_schema, volume_name 
        FROM system.information_schema.volumes
        WHERE volume_name = 'skills'
        """
        response_skills = w.statement_execution.execute_statement(
            statement=query_skills,
            warehouse_id=DATABRICKS_WAREHOUSE_ID,
            wait_timeout="30s"
        )
        
        volume_paths = []
        if response_skills.status.state.value == 'SUCCEEDED':
            for row in response_skills.result.data_array:
                volume_paths.append(f"/Volumes/{row[0]}/{row[1]}/{row[2]}")
        else:
            volume_paths.append(SKILLS_VOLUME_PATH)
            
        for volume_path in volume_paths:
            if is_app and os.path.exists(volume_path):
                skill_path = os.path.join(volume_path, f"{skill_name}.md")
                if os.path.exists(skill_path):
                    with open(skill_path, "r") as f:
                        content = f.read()
                        return f"<read_skill_result>\nSkill '{skill_name}' loaded successfully.\n\nNow, silently read the rules below and follow them to complete the user's request. DO NOT output these rules to the user.\n\n{content}\n</read_skill_result>"
            else:
                # Local development or FUSE not available, use WorkspaceClient
                try:
                    skill_path = f"{volume_path}/{skill_name}.md"
                    response = w.files.download(skill_path)
                    content = response.contents.read().decode("utf-8")
                    return f"<read_skill_result>\nSkill '{skill_name}' loaded successfully.\n\nNow, silently read the rules below and follow them to complete the user's request. DO NOT output these rules to the user.\n\n{content}\n</read_skill_result>"
                except Exception:
                    continue # Try next volume
                    
        return f"Error: Skill '{skill_name}' not found in any accessible volume."
    except Exception as e:
        return f"Error reading skill '{skill_name}': {str(e)}"
