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

def get_langchain_tools(w=None):
    """
    Discovers all tools dynamically and wraps them as LangChain tools.
    """
    from langchain_core.tools import tool
    import os
    
    langchain_tools = []
    
    # Use Databricks Langchain UCFunctionToolkit to load tools
    try:
        from databricks_langchain import UCFunctionToolkit
        from backend.agent.config import CATALOG_SCHEMA
        from databricks.sdk import WorkspaceClient
        
        # Initialize the WorkspaceClient if not provided
        if w is None:
            is_app = bool(os.environ.get("DATABRICKS_APP_NAME"))
            if is_app:
                w = WorkspaceClient()
            else:
                profile = os.getenv("DATABRICKS_PROFILE", "myenv")
                w = WorkspaceClient(profile=profile)
                
        # Dynamically discover tools the user has access to
        from backend.agent.config import DATABRICKS_WAREHOUSE_ID, CATALOG_SCHEMA
        catalog = CATALOG_SCHEMA.split('.')[0]
        schema = CATALOG_SCHEMA.split('.')[1]
        func_names = []
        try:
            query_tools = f"""
            SELECT routine_catalog, routine_schema, routine_name 
            FROM system.information_schema.routines 
            WHERE routine_type = 'FUNCTION' 
            AND routine_catalog = '{catalog}'
            AND routine_schema = '{schema}'
            """
            response_tools = w.statement_execution.execute_statement(
                statement=query_tools,
                warehouse_id=DATABRICKS_WAREHOUSE_ID,
                wait_timeout="30s"
            )
            if response_tools.status.state.value == 'SUCCEEDED':
                if response_tools.result.data_array:
                    for row in response_tools.result.data_array:
                        func_names.append(f"{row[0]}.{row[1]}.{row[2]}")
        except Exception as e:
            print(f"Warning: Failed to dynamically discover tools: {e}")
            # Fallback to config schema if dynamic discovery fails
            func_names = [
                f"{CATALOG_SCHEMA}.get_inventory",
                f"{CATALOG_SCHEMA}.get_supplier_lead_times",
                f"{CATALOG_SCHEMA}.draft_purchase_order",
                f"{CATALOG_SCHEMA}.manage_safety_stock",
                f"{CATALOG_SCHEMA}.list_genies",
                f"{CATALOG_SCHEMA}.ask_genie",
                f"{CATALOG_SCHEMA}.notify_slack_channel",
                f"{CATALOG_SCHEMA}.get_erp_supplier_status"
            ]
            
        # Set the default client for Unity Catalog
        try:
            from unitycatalog.ai.core.client import set_uc_function_client
            from unitycatalog.ai.core.databricks import DatabricksFunctionClient
            
            uc_client = DatabricksFunctionClient(client=w)
            set_uc_function_client(uc_client)
        except ImportError:
            # unitycatalog-ai <= 0.3.x compatibility
            try:
                from databricks_langchain.uc_function_toolkit import set_uc_function_client
                set_uc_function_client(w)
            except ImportError:
                pass
            
        toolkit = UCFunctionToolkit(function_names=func_names)
        langchain_tools.extend(toolkit.tools)
    except Exception as e:
        print(f"Warning: Failed to load UC tools: {e}")
        print("Falling back to local Python tools...")
        import pkgutil
        import importlib
        import backend.tools.mcp
        
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
                
    return langchain_tools

def discover_skills(w=None):
    """
    Discovers all skills dynamically from the Unity Catalog volume.
    Returns a string formatted for the system prompt.
    """
    import os
    from backend.agent.config import SKILLS_VOLUME_PATH
    
    skills = []
    
    try:
        # If we're in Databricks Apps, we can just read from the FUSE mount directly
        is_app = bool(os.environ.get("DATABRICKS_APP_NAME"))
        
        # We will dynamically discover skills across all catalogs/schemas the user has access to
        from backend.agent.config import DATABRICKS_WAREHOUSE_ID
        
        # Initialize the WorkspaceClient if not provided
        if w is None:
            from databricks.sdk import WorkspaceClient
            if is_app:
                w = WorkspaceClient()
            else:
                profile = os.getenv("DATABRICKS_PROFILE", "myenv")
                w = WorkspaceClient(profile=profile)
                
        # Query for skills (volumes named 'skills')
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
            if response_skills.result.data_array:
                for row in response_skills.result.data_array:
                    volume_paths.append(f"/Volumes/{row[0]}/{row[1]}/{row[2]}")
        else:
            # Fallback to config path
            volume_paths.append(SKILLS_VOLUME_PATH)
            
        for volume_path in volume_paths:
            if is_app and os.path.exists(volume_path):
                for filename in os.listdir(volume_path):
                    if filename.endswith(".md"):
                        skill_name = filename[:-3]
                        filepath = os.path.join(volume_path, filename)
                        
                        description = "No description provided."
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
                        except Exception as e:
                            print(f"Error reading skill {filename}: {e}")
                            
                        skills.append(f"- `{skill_name}`: {description}")
            else:
                # Local development or FUSE not available, use WorkspaceClient
                try:
                    files = w.files.list_directory_contents(volume_path)
                    for file_info in files:
                        if file_info.path.endswith(".md"):
                            filename = os.path.basename(file_info.path)
                            skill_name = filename[:-3]
                            
                            description = "No description provided."
                            try:
                                # Download the file content
                                response = w.files.download(file_info.path)
                                content = response.contents.read().decode("utf-8")
                                lines = content.split("\n")
                                if len(lines) > 2 and lines[0].strip() == "---":
                                    for line in lines[1:]:
                                        if line.strip() == "---":
                                            break
                                        if line.startswith("description:"):
                                            description = line.replace("description:", "").strip()
                                            break
                            except Exception as e:
                                print(f"Error downloading skill {filename}: {e}")
                                
                            skills.append(f"- `{skill_name}`: {description}")
                except Exception as e:
                    print(f"Error listing skills volume {volume_path}: {e}")
                    
    except Exception as e:
        print(f"Error in discover_skills: {e}")
            
    if not skills:
        return ""
        
    skills_str = "\n".join(skills)
    return f"\n\nYou have access to the following skills. If a user asks about these topics, use the `read_skill` tool to read the instructions before answering:\n{skills_str}"
