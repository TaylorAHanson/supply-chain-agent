import mlflow
from backend.agent.config import MODEL_NAME, CATALOG_SCHEMA, LLM_ENDPOINT_URL, MAX_TOKENS, LLM_MODEL_NAME
import os
from typing import Generator

class SupplyChainLangGraphAgent(mlflow.pyfunc.ResponsesAgent):
    def __init__(self):
        super().__init__()
        self.agent = None

    def load_context(self, context):
        import os
        from databricks.sdk import WorkspaceClient
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent
        from backend.tools.registry import get_langchain_tools, discover_skills
        
        # Initialize Databricks SDK
        self.w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))
        
        # Get authentication token and host
        headers = self.w.config.authenticate()
        if isinstance(headers, dict) and "Authorization" in headers:
            token = headers["Authorization"].replace("Bearer ", "")
        else:
            token = self.w.config.token
        host = self.w.config.host.rstrip('/')
        
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
            
        system_prompt += discover_skills()
        
        # Get Tools
        tools = get_langchain_tools()
        
        # Create the LangGraph agent
        self.agent = create_react_agent(llm, tools, prompt=system_prompt)

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

    def predict(self, request: mlflow.types.responses.ResponsesAgentRequest) -> mlflow.types.responses.ResponsesAgentResponse:
        """Non-streaming predict: collects all streaming chunks into a single response."""
        output_items = []
        custom_outputs = {}
        for stream_event in self.predict_stream(request):
            event_type = getattr(stream_event, "type", None) if not isinstance(stream_event, dict) else stream_event.get("type")
            if event_type in ["response.output_item.done", "output_item.done"]:
                item = getattr(stream_event, "item", None) if not isinstance(stream_event, dict) else stream_event.get("item")
                if item:
                    output_items.append(item)
                
                # Check if custom_outputs was attached directly to the done event (monkey patch)
                if hasattr(stream_event, "custom_outputs"):
                    custom_outputs = getattr(stream_event, "custom_outputs", {})
                elif isinstance(stream_event, dict) and "custom_outputs" in stream_event:
                    custom_outputs = stream_event.get("custom_outputs", {})
            elif event_type == "custom_outputs":
                custom_outputs = getattr(stream_event, "custom_outputs", {}) if not isinstance(stream_event, dict) else stream_event.get("custom_outputs", {})
                
        return mlflow.types.responses.ResponsesAgentResponse(
            output=output_items,
            custom_outputs=custom_outputs
        )
        
    def predict_stream(
        self, request: mlflow.types.responses.ResponsesAgentRequest
    ) -> Generator[mlflow.types.responses.ResponsesAgentStreamEvent, None, None]:
        import uuid
        
        messages = self.prep_msgs_for_llm([i.model_dump() for i in request.input])
        input_len = len(messages)
        
        item_id = str(uuid.uuid4())
        aggregated_stream = ""
        
        # Stream events from LangGraph
        config = {"configurable": {"thread_id": "default_thread"}}
        if hasattr(request, "custom_inputs") and request.custom_inputs:
            config = {"configurable": {"thread_id": request.custom_inputs.get("session_id", "default_thread")}}
        
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
                        yield self.create_text_delta(delta=new_delta, item_id=item_id)
                elif chunk == aggregated_stream:
                    # Duplicate payload, ignore
                    pass
                elif len(aggregated_stream) > 0 and aggregated_stream.startswith(chunk):
                    # Out of order or partial chunk, ignore
                    pass
                # Otherwise, it's a standard additive delta
                else:
                    yield self.create_text_delta(delta=chunk, item_id=item_id)
                    aggregated_stream += chunk
                    
        # Extract tool calls from the final state to return as custom outputs
        tool_calls_executed = []
        try:
            final_state = self.agent.get_state(config)
            if final_state and hasattr(final_state, "values") and "messages" in final_state.values:
                new_messages = final_state.values["messages"][input_len:]
                for m in new_messages:
                    if hasattr(m, "tool_calls") and m.tool_calls:
                        for tc in m.tool_calls:
                            tool_name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                            if tool_name and tool_name.strip() != "":
                                tool_calls_executed.append({"tool_name": tool_name, "status": "executed inside agent"})
        except Exception:
            pass # State might not be available without a checkpointer
                        
        # Ensure we always yield at least ONE event if nothing was yielded so we don't get a 404 or hung stream
        if not aggregated_stream:
            # Send an empty string since yielding literal spaces might cause that weird white box
            pass
            
        # We want to filter out any skill leakage that somehow made its way into the final stream
        # If the LLM just printed out <system_instruction> tags, try to hide them
        if "<read_skill_result>" in aggregated_stream:
            import re
            aggregated_stream = re.sub(r'<read_skill_result>.*?</read_skill_result>', '', aggregated_stream, flags=re.DOTALL)
            
        # Yield the custom outputs event (this is a bit of a hack since StreamEvent doesn't natively have custom_outputs, 
        # but we can attach it to the final done event or yield a dummy event)
        done_event = mlflow.types.responses.ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(text=aggregated_stream, id=item_id)
        )
        # Monkey patch custom_outputs onto the event so our wrapper can catch it, 
        # though standard Databricks serving might ignore it on the stream end.
        done_event.custom_outputs = {"tool_calls": tool_calls_executed}
        yield done_event

def log_agent_model():
    """
    Log the ResponsesAgent model to MLflow Unity Catalog.
    """
    # MLflow ResponsesAgent handles signature inference automatically
    with mlflow.start_run() as run:
        # Define artifacts that the model depends on (like prompt files)
        import os
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        prompt_path = os.path.join(backend_dir, "agent", "prompt.md")
        
        artifacts = {
            "prompt": prompt_path
        }
        
        # We specify our custom wrapper class via code-based logging to avoid serialization issues
        model_info = mlflow.pyfunc.log_model(
            artifact_path="agent",
            python_model="backend/agent/model.py",
            artifacts=artifacts,
            registered_model_name=MODEL_NAME,
            pip_requirements=[
                "mlflow==3.10.1", 
                "pandas==2.3.3", 
                "databricks-sdk==0.102.0", 
                "openai>=1.14.3",
                "langchain>=0.2.0",
                "langchain-core>=0.2.0",
                "langchain-openai>=0.1.0",
                "langgraph>=0.1.0"
            ],
            code_paths=["backend"]
        )
        print(f"Logged LangGraph ResponsesAgent successfully to UC. Version: {model_info.registered_model_version}")
        return model_info.registered_model_version

if __name__ == "__main__":
    pass

# For code-based logging in Databricks AI Framework
mlflow.models.set_model(SupplyChainLangGraphAgent())
