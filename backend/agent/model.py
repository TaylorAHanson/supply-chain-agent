import os
from typing import Generator
import uuid
import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    output_to_responses_items_stream,
    to_chat_completions_input,
)
from backend.agent.config import CATALOG_SCHEMA, MAX_TOKENS, LLM_MODEL_NAME

class SupplyChainLangGraphAgent(ResponsesAgent):
    def __init__(self):
        self.agent = None

    def load_context(self, context=None, user_token=None):
        import os
        from databricks.sdk import WorkspaceClient
        from langchain_openai import ChatOpenAI
        from langchain.agents import create_agent
        from backend.tools.registry import get_langchain_tools, discover_skills
        
        # Initialize Databricks SDK
        is_app = bool(os.environ.get("DATABRICKS_APP_NAME"))
        if user_token:
            # Use On-Behalf-Of (OBO) authentication
            self.w = WorkspaceClient(token=user_token, auth_type="pat")
        elif is_app:
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
        
        # Create Langchain LLM pointing to Databricks Foundation Model Serving / AI Gateway Route
        base_url = f"{host}/ai-gateway/mlflow/v1" if "gateway" in LLM_MODEL_NAME or "endpoint" in LLM_MODEL_NAME else f"{host}/serving-endpoints"
        llm = ChatOpenAI(
            model=LLM_MODEL_NAME, # This should be the AI Gateway route name (e.g. supply-chain-agent-endpoint)
            api_key=token,
            base_url=base_url,
            streaming=False # AI Gateway with Output Guardrails does not support streaming
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
        system_prompt += discover_skills(w=self.w)
        
        # Get Tools
        tools = get_langchain_tools(w=self.w)
        
        # Create the LangGraph agent
        self.agent = create_agent(llm, tools, system_prompt=system_prompt)

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(output=outputs, custom_outputs=request.custom_inputs)

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        # Convert MLflow input messages to Langchain format
        cc_msgs = to_chat_completions_input([i.model_dump() for i in request.input])
        
        session_id = "default_thread"
        if request.custom_inputs and "session_id" in request.custom_inputs:
            session_id = request.custom_inputs["session_id"]
            
        config = {"configurable": {"thread_id": session_id}}
        
        item_id = str(uuid.uuid4())
        aggregated_stream = ""
        tool_calls_executed = []
        
        # AI Gateway with Output Guardrails does not support streaming, so we use invoke
        result = self.agent.invoke({"messages": cc_msgs}, config=config)
        
        # Parse the result
        for msg in result.get("messages", []):
            if type(msg).__name__ in ["AIMessage", "AIMessageChunk"]:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                        if tool_name and tool_name.strip() != "":
                            if not any(t["tool_name"] == tool_name for t in tool_calls_executed):
                                tool_calls_executed.append({"tool_name": tool_name, "status": "executed inside agent"})
        
        last_msg = result.get("messages", [])[-1] if result.get("messages") else None
        
        if last_msg and type(last_msg).__name__ in ["AIMessage", "AIMessageChunk"]:
            if hasattr(last_msg, "content"):
                if isinstance(last_msg.content, str):
                    aggregated_stream = last_msg.content
                elif isinstance(last_msg.content, list) and len(last_msg.content) > 0:
                    chunk_dict = last_msg.content[0]
                    if isinstance(chunk_dict, dict) and "text" in chunk_dict:
                        aggregated_stream = chunk_dict["text"]
                    elif isinstance(chunk_dict, str):
                        aggregated_stream = chunk_dict
        
        import re
        if "<read_skill_result>" in aggregated_stream:
            aggregated_stream = re.sub(r'<read_skill_result>.*?</read_skill_result>', '', aggregated_stream, flags=re.DOTALL)
            
        # Yield the whole text as a single delta
        if aggregated_stream:
            yield ResponsesAgentStreamEvent(
                **self.create_text_delta(delta=aggregated_stream, item_id=item_id)
            )
            
        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(
                text=aggregated_stream,
                id=item_id
            ),
            custom_outputs={"tool_calls": tool_calls_executed}
        )

def log_agent_model():
    import mlflow
    mlflow.langchain.autolog()
    
    with mlflow.start_run():
        logged_agent_info = mlflow.pyfunc.log_model(
            python_model="backend/agent/model.py",
            name="supply-chain-agent",
            artifacts={"prompt": "backend/agent/prompt.md"}
        )
        return logged_agent_info

if __name__ == "__main__":
    pass
