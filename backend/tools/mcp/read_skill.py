import os

def read_skill(skill_name: str) -> str:
    """
    Reads the contents of a specific skill document. Use this to read the instructions for a given skill.
    
    :param skill_name: The name of the skill to read (e.g., 'analyze_safety_stock').
    """
    skills_dir = os.path.join(os.path.dirname(__file__), "..", "..", "skills")
    skill_path = os.path.join(skills_dir, f"{skill_name}.md")
    
    if not os.path.exists(skill_path):
        return f"Error: Skill '{skill_name}' not found."
        
    try:
        with open(skill_path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading skill '{skill_name}': {str(e)}"
