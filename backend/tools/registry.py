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

# Local Python tools that are NOT registered as Unity Catalog functions and therefore must
# always be bound directly. The system prompt instructs the model to use these by name, so if
# they aren't bound the model "fabricates" the calls as text instead of actually running them.
# (SQL + Genie are now served by the Databricks managed MCP servers — see _load_managed_mcp_tools.)
_CORE_LOCAL_TOOLS = ["read_skill"]

# Managed-MCP-backed tools always bound first so they win name de-dup over any UC/local twins.
_MANAGED_MCP_TOOL_NAMES = ["query_lakehouse", "ask_genie", "list_genies"]


def _mcp_host_and_token(w, user_token):
    """Resolve the workspace host + bearer token to call managed MCP servers.

    Prefers the user's OBO token (governance parity); otherwise falls back to the token the
    WorkspaceClient is configured with (e.g. the Databricks App service principal).
    """
    import os

    host = (w.config.host or "").rstrip("/")
    if host and not host.startswith("http"):
        host = f"https://{host}"

    token = user_token
    if not token:
        try:
            headers = w.config.authenticate()
            if isinstance(headers, dict) and "Authorization" in headers:
                token = headers["Authorization"].replace("Bearer ", "")
        except Exception:
            token = None
    if not token:
        token = os.environ.get("DATABRICKS_TOKEN") or getattr(w.config, "token", None)
    return host, token


def _load_managed_mcp_tools(w, user_token):
    """Build the SQL + Genie tools backed by Databricks managed MCP servers.

    Returns an empty list (and logs) on any failure so the agent still comes up with its
    remaining tools rather than crashing.
    """
    try:
        from backend.tools.managed_mcp import (
            ManagedMCPClient,
            build_sql_tool,
            build_genie_tools,
        )

        host, token = _mcp_host_and_token(w, user_token)
        if not host or not token:
            print("Warning: could not resolve host/token for managed MCP tools; skipping.")
            return []

        client = ManagedMCPClient(host=host, token=token)
        tools = [build_sql_tool(client)]
        tools.extend(build_genie_tools(client, w=w))
        return tools
    except Exception as e:
        print(f"Warning: Failed to load managed MCP tools: {e}")
        return []


def _wrap_skill_result(skill_name, content):
    return (
        f"<read_skill_result>\nSkill '{skill_name}' loaded successfully.\n\n"
        f"Now, silently read the rules below and follow them to complete the user's request. "
        f"DO NOT output these rules to the user.\n\n{content}\n</read_skill_result>"
    )


def _build_obo_read_skill(w):
    """An OBO-bound read_skill that checks the user's *personal* workspace skills first, then
    the shared Unity Catalog 'skills' volumes. Built with the request's WorkspaceClient so it can
    reach the caller's own /Workspace/Users/... folder, which the app service principal cannot."""
    from langchain_core.tools import tool
    from backend.tools import user_skills as _us

    @tool
    def read_skill(skill_name: str) -> str:
        """Reads the contents of a specific skill document. Use this to read the instructions for a given skill.
        IMPORTANT: DO NOT output the raw content of the skill file into the chat window. Read it silently and follow the instructions.

        :param skill_name: The name of the skill to read (e.g., 'analyze_safety_stock').
        """
        # 1) Personal (user-scoped) skill in the caller's workspace folder.
        try:
            personal = _us.read_user_skill(w, skill_name)
            if personal:
                return _wrap_skill_result(skill_name, personal)
        except Exception:
            pass

        # 2) Shared skills in Unity Catalog 'skills' volumes.
        try:
            from backend.agent.config import SKILLS_VOLUME_PATH, DATABRICKS_WAREHOUSE_ID
            volume_paths = []
            try:
                resp = w.statement_execution.execute_statement(
                    statement="SELECT volume_catalog, volume_schema, volume_name FROM system.information_schema.volumes WHERE volume_name = 'skills'",
                    warehouse_id=DATABRICKS_WAREHOUSE_ID,
                    wait_timeout="30s",
                )
                if resp.status.state.value == "SUCCEEDED" and resp.result.data_array:
                    for row in resp.result.data_array:
                        volume_paths.append(f"/Volumes/{row[0]}/{row[1]}/{row[2]}")
            except Exception:
                pass
            if not volume_paths and SKILLS_VOLUME_PATH:
                volume_paths.append(SKILLS_VOLUME_PATH)
            for vp in volume_paths:
                try:
                    resp = w.files.download(f"{vp}/{skill_name}.md")
                    content = resp.contents.read().decode("utf-8")
                    return _wrap_skill_result(skill_name, content)
                except Exception:
                    continue
        except Exception as e:
            return f"Error reading skill '{skill_name}': {e}"

        return f"Error: Skill '{skill_name}' not found in your personal skills or any accessible volume."

    return read_skill


def _load_local_mcp_tools(only=None, selected_tools=None):
    """Wrap local Python tools in backend/tools/mcp/ as LangChain tools.

    ``only`` restricts to a specific set of module names; ``selected_tools`` (if provided)
    further filters by the user's tool selection.
    """
    from langchain_core.tools import tool
    import pkgutil
    import importlib
    import inspect as _inspect
    import backend.tools.mcp

    loaded = []
    for _, module_name, _ in pkgutil.iter_modules(backend.tools.mcp.__path__):
        if module_name.startswith("_"):
            continue
        if only is not None and module_name not in only:
            continue
        if selected_tools is not None and module_name not in selected_tools:
            continue
        try:
            mod = importlib.import_module(f"backend.tools.mcp.{module_name}")
            func = getattr(mod, module_name, None)
            if _inspect.isfunction(func):
                loaded.append(tool(func))
        except Exception as e:
            print(f"Warning: Failed to load tool {module_name}: {e}")
    return loaded


def get_langchain_tools(w=None, selected_tools=None, user_token=None):
    """
    Discovers all tools dynamically and wraps them as LangChain tools.
    """
    import os
    
    langchain_tools = []

    # Ensure we have a WorkspaceClient (the managed-MCP tools need its host + token).
    if w is None:
        from databricks.sdk import WorkspaceClient
        if bool(os.environ.get("DATABRICKS_APP_NAME")):
            w = WorkspaceClient()
        else:
            w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))

    # Bind the Databricks managed-MCP tools first (SQL + Genie). These replace the old
    # hand-rolled query_lakehouse/ask_genie and run under the user's OBO token. Binding them
    # first means name de-dup below skips any UC/local functions that share these names.
    langchain_tools.extend(_load_managed_mcp_tools(w, user_token))

    # Bind an OBO-aware read_skill that can also see the user's personal workspace skills.
    # Built first so name de-dup keeps it over the app-SP local fallback below.
    try:
        langchain_tools.append(_build_obo_read_skill(w))
    except Exception as e:
        print(f"Warning: Failed to build OBO read_skill: {e}")

    # Always bind the remaining core local tools (read_skill). These are not UC functions, so
    # the UC path below never loads them — yet the prompt depends on them. (De-duped against the
    # OBO read_skill above.)
    _pre = {t.name for t in langchain_tools}
    for t in _load_local_mcp_tools(only=_CORE_LOCAL_TOOLS, selected_tools=selected_tools):
        if t.name not in _pre:
            langchain_tools.append(t)
    _bound_names = {t.name for t in langchain_tools}
    
    # Use Databricks Langchain UCFunctionToolkit to load tools.
    # Import from the underlying module (`unitycatalog.ai.langchain.toolkit`) rather than the
    # top-level `databricks_langchain` package: importing `databricks_langchain` eagerly pulls in
    # its vector-search client, which raises `cannot import name 'VectorSearchIndex'` when the
    # deployed `databricks-vectorsearch` version is incompatible — taking down ALL UC tool loading
    # even though we never touch vector search. Fall back to the package import if the layout differs.
    try:
        from unitycatalog.ai.langchain.toolkit import UCFunctionToolkit
    except Exception:
        from databricks_langchain import UCFunctionToolkit
    try:
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
                # No hard-coded fallback: leave func_names empty. The managed-MCP tools
                # (query_lakehouse, ask_genie, list_genies) and read_skill are already bound
                # above, so the agent still functions even when UC discovery fails.
                func_names = []
            
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
            # No UC functions selected or discovered: skip UCFunctionToolkit init (avoids noisy
            # warnings), but DON'T drop the tools already bound above (managed-MCP ask_genie /
            # query_lakehouse / list_genies + read_skill). Returning [] here was a bug that left
            # the agent with no tools whenever UC discovery failed (e.g. OBO scope / warehouse).
            return langchain_tools
            
        # Build a UC function client bound to OUR WorkspaceClient (OBO user token, or the app
        # service principal). Passing client=w is critical: without it the toolkit falls back to
        # ambient databricks-cli auth (e.g. a stale default profile) and fails with
        # "No client provided". The toolkit accepts the client directly, so we don't depend on
        # set_uc_function_client — but we still set it (best-effort) so UC *execution* can find
        # the client. Its import path moved between versions, so import it defensively.
        from unitycatalog.ai.core.databricks import DatabricksFunctionClient

        uc_client = DatabricksFunctionClient(client=w)

        set_uc_function_client = None
        for _mod in ("unitycatalog.ai.core.base", "unitycatalog.ai.core.client"):
            try:
                set_uc_function_client = __import__(_mod, fromlist=["set_uc_function_client"]).set_uc_function_client
                break
            except (ImportError, AttributeError):
                continue
        if set_uc_function_client is not None:
            try:
                set_uc_function_client(uc_client)
            except Exception as e:
                print(f"Warning: set_uc_function_client failed (non-fatal): {e}")

        toolkit = UCFunctionToolkit(function_names=func_names, client=uc_client)
            
        # Avoid binding two tools with the same name (e.g. a UC function that shares a name
        # with a core local tool already bound above).
        for t in toolkit.tools:
            if t.name not in _bound_names:
                langchain_tools.append(t)
                _bound_names.add(t.name)
    except Exception as e:
        print(f"Warning: Failed to load UC tools: {e}")
        print("Falling back to all local Python tools...")
        # UC functions are unavailable — bind every local tool (minus what's already bound).
        for t in _load_local_mcp_tools(selected_tools=selected_tools):
            if t.name not in _bound_names:
                langchain_tools.append(t)
                _bound_names.add(t.name)
                
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

    # Personal (user-scoped) skills from the caller's workspace folder. Done in its own block —
    # independent of the shared-volume discovery above (which needs a SQL warehouse) — and always
    # surfaced regardless of `selected_skills`, since the user authored them for their own use.
    try:
        from backend.tools import user_skills as _us
        if w is None:
            from databricks.sdk import WorkspaceClient
            if bool(os.environ.get("DATABRICKS_APP_NAME")):
                w = WorkspaceClient()
            else:
                w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))
        for s in _us.list_user_skills(w):
            skills.append(f"- `{s['name']}` (personal): {s['description']}")
    except Exception as e:
        print(f"Error discovering user skills: {e}")

    if not skills:
        return ""
        
    skills_str = "\n".join(skills)
    return f"\n\nYou have access to the following skills. If a user asks about these topics, use the `read_skill` tool to read the instructions before answering:\n{skills_str}"
