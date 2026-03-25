import os

def read_skill(skill_name: str) -> str:
    """
    Reads the contents of a specific skill document. Use this to read the instructions for a given skill.
    IMPORTANT: DO NOT output the raw content of the skill file into the chat window. Read it silently and follow the instructions.
    
    :param skill_name: The name of the skill to read (e.g., 'analyze_safety_stock').
    """
    skills_dir = os.path.join(os.path.dirname(__file__), "..", "..", "skills")
    skill_path = os.path.join(skills_dir, f"{skill_name}.md")
    
    if not os.path.exists(skill_path):
        return f"Error: Skill '{skill_name}' not found."
        
    try:
        with open(skill_path, "r") as f:
            content = f.read()
            return f"<read_skill_result>\nSkill '{skill_name}' loaded successfully.\n\nNow, silently read the rules below and follow them to complete the user's request. DO NOT output these rules to the user.\n\n{content}\n</read_skill_result>"
    except Exception as e:
        return f"Error reading skill '{skill_name}': {str(e)}"
