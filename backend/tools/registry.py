import inspect

def get_openai_tool_schema(func):
    """
    Dynamically generates an OpenAI function calling schema from a Python function's signature and docstring.
    """
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or f"Execute {func.__name__}"
    
    properties = {}
    required = []
    
    for name, param in sig.parameters.items():
        if name == "self": continue
        
        param_type = "string"
        if param.annotation == int: param_type = "integer"
        elif param.annotation == float: param_type = "number"
        elif param.annotation == bool: param_type = "boolean"
        elif param.annotation == list: param_type = "array"
        elif param.annotation == dict: param_type = "object"
        
        properties[name] = {"type": param_type, "description": f"The {name} parameter"}
        if param.default == inspect.Parameter.empty:
            required.append(name)
            
    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": doc.strip(),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }

def discover_tools():
    """
    Discovers all tools dynamically from the codebase.
    Returns: list of OpenAI schemas, dict mapping tool_name -> execution_type
    """
    import backend.tools.uc_tools as uc_tools
    import pkgutil
    import importlib
    
    schemas = []
    execution_routing = {}
    
    # Discover Unity Catalog (UC) Tools
    for name, obj in inspect.getmembers(uc_tools, inspect.isfunction):
        if not name.startswith("_"):
            schemas.append(get_openai_tool_schema(obj))
            execution_routing[name] = "uc"
            
    # Discover FastMCP Tools dynamically from backend/tools/mcp/ directory
    import backend.tools.mcp
    
    for _, module_name, _ in pkgutil.iter_modules(backend.tools.mcp.__path__):
        if module_name.startswith("_"): continue
        
        try:
            mod = importlib.import_module(f"backend.tools.mcp.{module_name}")
            
            # We assume the tool function name matches the filename
            if hasattr(mod, module_name):
                func = getattr(mod, module_name)
                if inspect.isfunction(func):
                    schemas.append(get_openai_tool_schema(func))
                    execution_routing[module_name] = "fastmcp"
        except Exception as e:
            print(f"Warning: Failed to load tool {module_name}: {e}")
            
    return schemas, execution_routing

def get_langchain_tools():
    """
    Discovers all tools dynamically and wraps them as LangChain tools.
    """
    from langchain_core.tools import tool
    import backend.tools.uc_tools as uc_tools
    import pkgutil
    import importlib
    import backend.tools.mcp
    
    langchain_tools = []
    
    # FastMCP Tools
    for _, module_name, _ in pkgutil.iter_modules(backend.tools.mcp.__path__):
        if module_name.startswith("_"): continue
        try:
            mod = importlib.import_module(f"backend.tools.mcp.{module_name}")
            if hasattr(mod, module_name):
                func = getattr(mod, module_name)
                if inspect.isfunction(func):
                    langchain_tools.append(tool(func))
        except Exception as e:
            print(f"Warning: Failed to load tool {module_name}: {e}")
                
    # Unity Catalog Tools
    import os
    import time
    from databricks.sdk import WorkspaceClient
    
    def create_uc_executor(func_name, original_func):
        def wrapper(**kwargs):
            try:
                from backend.agent.config import CATALOG_SCHEMA
            except ImportError:
                CATALOG_SCHEMA = os.getenv("CATALOG_SCHEMA", "taylor_hanson_build_catalog.supply_chain_schema")
            
            try:
                w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE") if not os.environ.get("DATABRICKS_APP_NAME") else None)
                
                warehouses = list(w.warehouses.list())
                wh_id = next((wh.id for wh in warehouses if wh.state.name in ['RUNNING', 'STARTING']), None)
                if not wh_id and warehouses: wh_id = warehouses[0].id
                if not wh_id: return "Error: No SQL warehouse found."
                
                # Construct SQL to call the UC function
                args_str = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in kwargs.values()])
                sql = f"SELECT * FROM {CATALOG_SCHEMA}.{func_name}({args_str})"
                
                res = w.statement_execution.execute_statement(statement=sql, warehouse_id=wh_id)
                
                while True:
                    status = w.statement_execution.get_statement(res.statement_id).status
                    if status.state.value in ["SUCCEEDED", "FAILED", "CANCELED", "CLOSED"]: break
                    time.sleep(1)
                    
                if status.state.value == "SUCCEEDED":
                    result = w.statement_execution.get_statement(res.statement_id)
                    if result.result and result.result.data_array:
                        columns = [col.name for col in result.manifest.schema.columns] if result.manifest and result.manifest.schema else []
                        output = f"Columns: {columns}\nData:\n"
                        for row in result.result.data_array[:100]:
                            output += f"{row}\n"
                        return output
                    return f"Function executed successfully but returned no data."
                return f"SQL Failed: {status.error.message}"
            except Exception as e:
                return f"Error executing UC function: {str(e)}"
                
        # Copy metadata from original function to wrapper so LangChain tool creation sees the right schema
        wrapper.__name__ = func_name
        wrapper.__doc__ = inspect.getdoc(original_func)
        wrapper.__signature__ = inspect.signature(original_func)
        if hasattr(original_func, "__annotations__"):
            wrapper.__annotations__ = original_func.__annotations__
        return wrapper

    for name, obj in inspect.getmembers(uc_tools, inspect.isfunction):
        if not name.startswith("_"):
            executor = create_uc_executor(name, obj)
            langchain_tools.append(tool(executor))
            
    return langchain_tools

def discover_skills():
    """
    Discovers all skills dynamically from the backend/skills/ directory.
    Returns a string formatted for the system prompt.
    """
    import os
    skills_dir = os.path.join(os.path.dirname(__file__), "..", "skills")
    
    if not os.path.exists(skills_dir):
        return ""
        
    skills = []
    for filename in os.listdir(skills_dir):
        if filename.endswith(".md"):
            skill_name = filename[:-3]
            filepath = os.path.join(skills_dir, filename)
            
            description = "No description provided."
            # Extract description from the YAML frontmatter if it exists
            try:
                with open(filepath, "r") as f:
                    lines = f.readlines()
                    if len(lines) > 2 and lines[0].strip() == "---":
                        for line in lines[1:]:
                            if line.strip() == "---":
                                break
                            if line.startswith("description:"):
                                description = line.replace("description:", "").strip()
                                break
            except:
                pass
                
            skills.append(f"- `{skill_name}`: {description}")
            
    if not skills:
        return ""
        
    skills_str = "\n".join(skills)
    return f"\n\nYou have access to the following skills. If a user asks about these topics, use the `read_skill` tool to read the instructions before answering:\n{skills_str}"
