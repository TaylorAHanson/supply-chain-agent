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

def get_langchain_tools(w=None, selected_tools=None, user_token=None):
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
        
        func_names = []
        # Check SQLite Cache first
        import sqlite3
        import hashlib
        import json
        import time
        
        token_hash = hashlib.sha256(user_token.encode()).hexdigest() if user_token else "shared"
        cache_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools_skills_cache.db')
        
        cache_hit = False
        try:
            if os.path.exists(cache_db_path):
                conn = sqlite3.connect(cache_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT tools, timestamp FROM cache WHERE token_hash = ?", (token_hash,))
                row = cursor.fetchone()
                
                if row and (time.time() - row[1]) < 3600:
                    cached_tools = json.loads(row[0])
                    func_names = [t["name"] for t in cached_tools]
                    cache_hit = True
                conn.close()
        except Exception as e:
            print(f"Warning: Tool Cache read error {e}")
            
        # Initialize the WorkspaceClient if not provided (needed for execution even if cache hit)
        if w is None:
            is_app = bool(os.environ.get("DATABRICKS_APP_NAME"))
            if is_app:
                w = WorkspaceClient()
            else:
                profile = os.getenv("DATABRICKS_PROFILE", "myenv")
                w = WorkspaceClient(profile=profile)
                
        if not cache_hit:
            # Dynamically discover tools the user has access to
            from backend.agent.config import DATABRICKS_WAREHOUSE_ID, CATALOG_SCHEMA
            
            # Guard against undefined CATALOG_SCHEMA
            if CATALOG_SCHEMA:
                catalog = CATALOG_SCHEMA.split('.')[0]
                schema = CATALOG_SCHEMA.split('.')[1]
            else:
                catalog, schema = "system", "information_schema"
                
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
                default_catalog = CATALOG_SCHEMA if CATALOG_SCHEMA else "default.default"
                func_names = [
                    f"{default_catalog}.get_inventory",
                    f"{default_catalog}.get_supplier_lead_times",
                    f"{default_catalog}.draft_purchase_order",
                    f"{default_catalog}.manage_safety_stock",
                    f"{default_catalog}.list_genies",
                    f"{default_catalog}.ask_genie",
                    f"{default_catalog}.notify_slack_channel",
                    f"{default_catalog}.get_erp_supplier_status"
                ]
            
        # Save to cache if not already populated by the endpoint
        if not cache_hit:
            try:
                conn = sqlite3.connect(cache_db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO cache (token_hash, tools, skills, timestamp) VALUES (?, ?, ?, ?)",
                    (token_hash, json.dumps([{"name": f, "type": "UC Function"} for f in func_names]), json.dumps([]), time.time())
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Warning: Failed to save to cache {e}")
            
        if selected_tools is not None:
            func_names = [f for f in func_names if f in selected_tools]
            
        if not func_names:
            # No UC tools selected or discovered, don't try to initialize the toolkit to avoid warnings
            return []
            
        # Set the default client for Unity Catalog
        try:
            from unitycatalog.ai.core.client import set_uc_function_client
            from unitycatalog.ai.core.databricks import DatabricksFunctionClient
            
            is_app = bool(os.environ.get("DATABRICKS_APP_NAME"))
            if is_app:
                uc_client = DatabricksFunctionClient(client=w)
            else:
                prof = os.getenv("DATABRICKS_PROFILE", "myenv")
                uc_client = DatabricksFunctionClient(client=w, profile=prof)
                
            set_uc_function_client(uc_client)
            
            # Use **kwargs to avoid passing unexpected kwargs if the class signature has changed
            toolkit_kwargs = {"function_names": func_names, "client": uc_client}
            
            try:
                toolkit = UCFunctionToolkit(**toolkit_kwargs)
            except Exception as inner_e:
                if "unexpected keyword argument 'client'" in str(inner_e) or "Extra inputs are not permitted" in str(inner_e):
                    # Try without client if it's not supported by this version
                    toolkit = UCFunctionToolkit(function_names=func_names)
                else:
                    raise inner_e
        except ImportError:
            # unitycatalog-ai <= 0.3.x compatibility
            try:
                from databricks_langchain.uc_function_toolkit import set_uc_function_client
                set_uc_function_client(w)
                toolkit = UCFunctionToolkit(function_names=func_names)
            except ImportError:
                # If set_uc_function_client is not available, some older versions
                # allow WorkspaceClient to be passed as workspace_client
                try:
                    toolkit = UCFunctionToolkit(function_names=func_names, workspace_client=w)
                except Exception:
                    try:
                        toolkit = UCFunctionToolkit(function_names=func_names, client=w)
                    except Exception:
                        toolkit = UCFunctionToolkit(function_names=func_names)
            
        langchain_tools.extend(toolkit.tools)
    except Exception as e:
        print(f"Warning: Failed to load UC tools: {e}")
        print("Falling back to local Python tools...")
        import pkgutil
        import importlib
        import inspect
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

def discover_skills(w=None, selected_skills=None, user_token=None):
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
        
        # Check SQLite Cache first
        import sqlite3
        import hashlib
        import json
        import time
        
        token_hash = hashlib.sha256(user_token.encode()).hexdigest() if user_token else "shared"
        cache_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools_skills_cache.db')
        
        cache_hit = False
        volume_paths = []
        try:
            if os.path.exists(cache_db_path):
                conn = sqlite3.connect(cache_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT skills, timestamp FROM cache WHERE token_hash = ?", (token_hash,))
                row = cursor.fetchone()
                
                if row and (time.time() - row[1]) < 3600:
                    # If we have cache hit, we don't need to do the discovery steps below,
                    # but since the cache only gives us the list of skill names, not their raw paths,
                    # we still need to just use the default volume path to read from
                    volume_paths = [SKILLS_VOLUME_PATH]
                    cache_hit = True
                conn.close()
        except Exception as e:
            print(f"Warning: Skill Cache read error {e}")
            
        # Initialize the WorkspaceClient if not provided (needed for execution even if cache hit)
        if w is None:
            from databricks.sdk import WorkspaceClient
            if is_app:
                w = WorkspaceClient()
            else:
                profile = os.getenv("DATABRICKS_PROFILE", "myenv")
                w = WorkspaceClient(profile=profile)
                
        if not cache_hit:
            # We will dynamically discover skills across all catalogs/schemas the user has access to
            from backend.agent.config import DATABRICKS_WAREHOUSE_ID
            
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
                        if selected_skills is not None and skill_name not in selected_skills:
                            continue
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
                            if selected_skills is not None and skill_name not in selected_skills:
                                continue
                            
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
