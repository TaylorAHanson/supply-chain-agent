import mlflow
from backend.agent.config import MODEL_NAME, CATALOG_SCHEMA, LLM_ENDPOINT_URL, MAX_TOKENS, LLM_MODEL_NAME
import json
import time

class SupplyChainPyFuncAgent(mlflow.pyfunc.PythonModel):
    def __init__(self, catalog_schema: str):
        self.catalog_schema = catalog_schema
        self.w = None

    def load_context(self, context):
        from databricks.sdk import WorkspaceClient
        import os
        self.w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))

    def predict(self, context, model_input):
        messages_input = []
        query = ""
        
        if hasattr(model_input, 'to_dict'):
            data = model_input.to_dict(orient="records")
            if data and len(data) > 0:
                query = data[0].get("query", "")
                messages_input = data[0].get("messages", [])
        elif isinstance(model_input, dict):
            query = model_input.get("query", "")
            messages_input = model_input.get("messages", [])
        else:
            query = str(model_input)
            
        import os
        prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
        with open(prompt_path, "r") as f:
            system_prompt = f.read()

        from backend.tools.registry import discover_tools, discover_skills
        tool_schemas, tool_routing = discover_tools()
        
        # Append available skills to the system prompt
        system_prompt += discover_skills()
        
        messages = [
            {
                "role": "system", 
                "content": system_prompt
            }
        ]
        
        # Append history if available, else just the single query
        if messages_input:
            messages.extend(messages_input)
        elif query:
            messages.append({"role": "user", "content": query})
        
        try:
            # 1. Ask the LLM what to do
            # Using the databricks-sdk python client for foundation models.
            # Some versions of the SDK do not map 'tools' as a direct kwarg to the query method,
            # so we pass it inside the generic json payload using a raw API call if needed,
            # but `WorkspaceClient.serving_endpoints.query` takes a dictionary of inputs for custom models.
            # For foundation models, it takes OpenAI-like kwargs, but since tools is missing, 
            # we use the raw REST API via the `w.api_client` or wrap it in custom_inputs.
            
            import os
            import requests
            
            headers = self.w.config.authenticate()
            if isinstance(headers, dict) and "Authorization" in headers:
                token = headers["Authorization"].replace("Bearer ", "")
            else:
                token = self.w.config.token
                
            # The OpenAI python client is incompatible with the latest httpx (0.28.1)
            # because httpx removed the 'proxies' kwarg, but openai still attempts to use it.
            # So, we'll manually formulate the REST API request instead to bypass the broken OpenAI client.
            url = f"{self.w.config.host.rstrip('/')}/serving-endpoints/{LLM_MODEL_NAME}/invocations"
            
            payload = {
                "messages": messages,
                "max_tokens": MAX_TOKENS
            }
            if tool_schemas:
                payload["tools"] = tool_schemas
                
            resp = requests.post(
                url, 
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload
            )
            
            if resp.status_code != 200:
                return [f"Agent Error during LLM request: {resp.text}"]
                
            resp_data = resp.json()
            choice = resp_data.get("choices", [{}])[0]
            message_dict = choice.get("message", {})
            
            # Reconstruct the expected object structure for backward compatibility in our code
            class MessageResponse:
                def __init__(self, m):
                    self.content = m.get("content")
                    self.tool_calls = None
                    if m.get("tool_calls"):
                        class ToolCallResponse:
                            def __init__(self, t):
                                self.id = t.get("id")
                                class FuncResponse:
                                    def __init__(self, f):
                                        self.name = f.get("name")
                                        args = f.get("arguments")
                                        if isinstance(args, dict):
                                            import json
                                            self.arguments = json.dumps(args)
                                        else:
                                            self.arguments = args
                                self.function = FuncResponse(t.get("function", {}))
                            def as_dict(self):
                                return {"id": self.id, "type": "function", "function": {"name": self.function.name, "arguments": self.function.arguments}}
                        self.tool_calls = [ToolCallResponse(t) for t in m.get("tool_calls")]
                
                def model_dump(self, **kwargs):
                    return message_dict
                    
            message = MessageResponse(message_dict)
            
            # Fallback for Databricks Foundation Model text-based tool calls
            if not message.tool_calls and message.content and "<function=" in message.content:
                import re
                match = re.search(r"<function=([^>]+)>(.*?)</function>", message.content, re.DOTALL)
                if match:
                    class FallbackFunc:
                        def __init__(self, name, arguments):
                            self.name = name
                            self.arguments = arguments
                    class FallbackToolCall:
                        def __init__(self, name, arguments):
                            self.id = "call_" + name
                            self.function = FallbackFunc(name, arguments)
                        def as_dict(self):
                            return {"id": self.id, "type": "function", "function": {"name": self.function.name, "arguments": self.function.arguments}}
                    message.tool_calls = [FallbackToolCall(match.group(1), match.group(2))]
            
            # 2. If it wants to call a tool, execute it!
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                # Dynamic Routing based on registry
                execution_type = tool_routing.get(func_name, "unknown")
                
                # Safe dump of the assistant message (handles fallback custom objects)
                if hasattr(message, "model_dump"):
                    try:
                        ast_msg = message.model_dump(exclude_none=True)
                    except:
                        ast_msg = {"role": "assistant", "content": message.content, "tool_calls": [tc.as_dict() if hasattr(tc, "as_dict") else tc for tc in message.tool_calls]}
                else:
                    ast_msg = {"role": "assistant", "content": message.content, "tool_calls": [tc.as_dict() if hasattr(tc, "as_dict") else tc for tc in message.tool_calls]}
                
                if execution_type == "uc":
                    # Convert dict args to SQL string args
                    # Note: We assume the order of args generated by LLM matches the SQL function signature,
                    # or we can rely on Databricks SQL named arguments which is safer but standard positional is easier here if args are simple.
                    # Actually, python dict is ordered by insertion, which might match the prompt, 
                    # but named arguments like `func(arg1 => 'value')` are supported in Databricks SQL.
                    sql_args = []
                    for k, v in args.items():
                        if isinstance(v, str):
                            sql_args.append(f"{k} => '{v}'")
                        else:
                            sql_args.append(f"{k} => {v}")
                            
                    sql = f"SELECT * FROM {self.catalog_schema}.{func_name}({', '.join(sql_args)})"
                    res = self._run_sql(sql)
                    
                    # 3. Pass result back to LLM for final answer
                    messages.append(ast_msg)
                    messages.append({
                        "role": "tool", 
                        "tool_call_id": tool_call.id, 
                        "name": func_name, 
                        "content": str(res)
                    })
                    
                    payload["messages"] = messages
                    final_resp = requests.post(
                        url, 
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                        json=payload
                    )
                    
                    if final_resp.status_code != 200:
                        return [f"Agent Error during final response: {final_resp.text}"]
                        
                    final_choice = final_resp.json().get("choices", [{}])[0]
                    return [final_choice.get("message", {}).get("content", "")]
                    
                elif execution_type == "fastmcp":
                    # FAST_MCP ROUTING: Return a special payload to tell FastAPI to execute this
                    return [json.dumps({
                        "type": "fastmcp_tool_call",
                        "tool": func_name,
                        "arguments": args,
                        "assistant_message": ast_msg,
                        "tool_call_id": tool_call.id
                    })]
                else:
                    return [f"Error: Unknown tool {func_name}"]
            else:
                # LLM just wanted to talk
                return [message.content]
                
        except Exception as e:
            return [f"Agent Error: {str(e)}"]
            
    def _run_sql(self, sql):
        warehouses = list(self.w.warehouses.list())
        wh_id = None
        for wh in warehouses:
            if wh.state.name in ['RUNNING', 'STARTING']:
                wh_id = wh.id
                break
        if not wh_id and len(warehouses) > 0:
            wh_id = warehouses[0].id
            
        res = self.w.statement_execution.execute_statement(
            statement=sql,
            warehouse_id=wh_id,
            wait_timeout="0s"
        )
        
        stmt_id = res.statement_id
        while True:
            status = self.w.statement_execution.get_statement(stmt_id).status
            if status.state.value in ["SUCCEEDED", "FAILED", "CANCELED", "CLOSED"]:
                break
            time.sleep(1)
            
        if status.state.value == "SUCCEEDED":
            result = self.w.statement_execution.get_statement(stmt_id)
            if result.result and result.result.data_array:
                return str(result.result.data_array)
            return "No data returned from UC."
        return f"SQL Failed: {status.error.message}"

def log_agent_model():
    """
    Log the agent model to MLflow Unity Catalog.
    """
    from mlflow.models.signature import infer_signature
    
    input_example = {"query": "Check stock for SKU-555"}
    output_example = ["The stock for SKU-555 is 15."]
    signature = infer_signature(input_example, output_example)
    
    with mlflow.start_run() as run:
        model_info = mlflow.pyfunc.log_model(
            artifact_path="agent",
            python_model=SupplyChainPyFuncAgent(catalog_schema=CATALOG_SCHEMA),
            registered_model_name=MODEL_NAME,
            signature=signature,
            input_example=input_example,
            pip_requirements=["mlflow==3.10.1", "pandas==2.2.0", "databricks-sdk==0.102.0", "openai==1.14.3"],
            code_paths=["backend"]
        )
        print(f"Logged agent model {MODEL_NAME} successfully to UC. Version: {model_info.registered_model_version}")
        return model_info.registered_model_version

if __name__ == "__main__":
    pass
