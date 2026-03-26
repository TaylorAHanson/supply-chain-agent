import os
from typing import Generator
from backend.agent.config import CATALOG_SCHEMA, MAX_TOKENS, LLM_MODEL_NAME

class SupplyChainLangGraphAgent:
    def __init__(self):
        self.agent = None

    def load_context(self, context=None):
        import os
        from databricks.sdk import WorkspaceClient
        from langchain_openai import ChatOpenAI
        from langchain.agents import create_agent
        from backend.tools.registry import get_langchain_tools, discover_skills
        
        # Initialize Databricks SDK
        is_app = bool(os.environ.get("DATABRICKS_APP_NAME"))
        if is_app:
            self.w = WorkspaceClient()
        else:
            profile = os.getenv("DATABRICKS_PROFILE", "myenv")
            self.w = WorkspaceClient(profile=profile)
        
        # Get authentication token and host
        headers = self.w.config.authenticate()
        if isinstance(headers, dict) and "Authorization" in headers:
            token = headers["Authorization"].replace("Bearer ", "")
        else:
            token = os.environ.get("DATABRICKS_TOKEN") or self.w.config.token
            
        host = self.w.config.host.rstrip('/')
        if is_app and host and not host.startswith("http"):
            host = f"https://{host}"
        
        # Create Langchain LLM pointing to Databricks Foundation Model Serving
        llm = ChatOpenAI(
            model=LLM_MODEL_NAME,
            api_key=token,
            base_url=f"{host}/serving-endpoints",
            max_tokens=MAX_TOKENS,
            streaming=True # Enable streaming on the LLM client
        )
        
        # Build System Prompt
        try:
            # When running in MLflow Model Serving, the context object provides the path
            if context and hasattr(context, "artifacts") and "prompt" in context.artifacts:
                prompt_path = context.artifacts["prompt"]
            else:
                prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
                
            with open(prompt_path, "r") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            # Fallback if file isn't bundled correctly
            system_prompt = "You are a helpful supply chain AI agent."
        
        # Get Skills
        system_prompt += discover_skills()
        
        # Get Tools
        tools = get_langchain_tools()
        
        # Create the LangGraph agent
        self.agent = create_agent(llm, tools, system_prompt=system_prompt)

    def prep_msgs_for_llm(self, messages):
        """Convert MLflow input messages to Langchain format."""
        langchain_msgs = []
        for msg in messages:
            # Langchain expects role and content
            langchain_msgs.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        return langchain_msgs

    def predict_stream(
        self, request
    ):
        import uuid
        
        # Get input messages
        if isinstance(request, dict) and "input" in request:
            raw_input = request["input"]
        else:
            raw_input = getattr(request, 'input', request)
            
        # Parse inputs
        parsed_msgs = []
        for i in raw_input:
            if isinstance(i, dict):
                parsed_msgs.append(i)
            elif hasattr(i, 'model_dump'):
                parsed_msgs.append(i.model_dump())
            else:
                # Fallback if it's some other object or just a string
                parsed_msgs.append({"role": "user", "content": str(i)})
                
        messages = self.prep_msgs_for_llm(parsed_msgs)
        input_len = len(messages)
        
        item_id = str(uuid.uuid4())
        aggregated_stream = ""
        tool_calls_executed = []
        
        # Stream events from LangGraph
        config = {"configurable": {"thread_id": "default_thread"}}
        if hasattr(request, "custom_inputs") and request.custom_inputs:
            config = {"configurable": {"thread_id": request.custom_inputs.get("session_id", "default_thread")}}
        elif isinstance(request, dict) and "custom_inputs" in request:
            config = {"configurable": {"thread_id": request["custom_inputs"].get("session_id", "default_thread")}}
            
        for event in self.agent.stream({"messages": messages}, stream_mode="messages", config=config):
            msg = event[0]
            
            # We ONLY want to stream AI generated text to the user, not tool results or human messages.
            if type(msg).__name__ not in ["AIMessageChunk", "AIMessage"]:
                continue
                
            chunk = ""
            if hasattr(msg, "content"):
                if isinstance(msg.content, str):
                    chunk = msg.content
                elif isinstance(msg.content, list) and len(msg.content) > 0:
                    chunk_dict = msg.content[0]
                    if isinstance(chunk_dict, dict) and "text" in chunk_dict:
                        chunk = chunk_dict["text"]
                    elif isinstance(chunk_dict, str):
                        chunk = chunk_dict
                            
            # Some tool call messages incorrectly pass the tool content or instructions back to stream
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                    if tool_name and tool_name.strip() != "":
                        if not any(t["tool_name"] == tool_name for t in tool_calls_executed):
                            tool_calls_executed.append({"tool_name": tool_name, "status": "executed inside agent"})
                continue
            if hasattr(msg, "tool_call_chunks") and msg.tool_call_chunks:
                continue
            if hasattr(msg, "invalid_tool_calls") and msg.invalid_tool_calls:
                continue
                
            if chunk:
                # Some implementations stream the *entire* message over and over again with the new character appended
                if len(chunk) > len(aggregated_stream) and chunk.startswith(aggregated_stream):
                    new_delta = chunk[len(aggregated_stream):]
                    if new_delta:
                        aggregated_stream = chunk
                        yield {
                            "type": "response.output_text.delta",
                            "delta": new_delta,
                            "item_id": item_id
                        }
                elif chunk == aggregated_stream:
                    # Duplicate payload, ignore
                    pass
                elif len(aggregated_stream) > 0 and aggregated_stream.startswith(chunk):
                    # Out of order or partial chunk, ignore
                    pass
                # Otherwise, it's a standard additive delta
                else:
                    yield {
                        "type": "response.output_text.delta",
                        "delta": chunk,
                        "item_id": item_id
                    }
                    aggregated_stream += chunk
                    
        # Ensure we always yield at least ONE event if nothing was yielded so we don't get a 404 or hung stream
        if not aggregated_stream:
            # Send an empty string since yielding literal spaces might cause that weird white box
            pass
            
        # We want to filter out any skill leakage that somehow made its way into the final stream
        # If the LLM just printed out <system_instruction> tags, try to hide them
        if "<read_skill_result>" in aggregated_stream:
            import re
            aggregated_stream = re.sub(r'<read_skill_result>.*?</read_skill_result>', '', aggregated_stream, flags=re.DOTALL)
            
        yield {
            "type": "response.output_item.done",
            "item": {
                "text": aggregated_stream,
                "id": item_id
            },
            "custom_outputs": {"tool_calls": tool_calls_executed}
        }

def log_agent_model():
    pass

if __name__ == "__main__":
    pass
