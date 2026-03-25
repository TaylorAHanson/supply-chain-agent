import mlflow
from backend.agent.config import MODEL_NAME, CATALOG_SCHEMA, LLM_ENDPOINT_URL, MAX_TOKENS, LLM_MODEL_NAME
import os

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
            max_tokens=MAX_TOKENS
        )
        
        # Build System Prompt
        prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
        with open(prompt_path, "r") as f:
            system_prompt = f.read()
            
        system_prompt += discover_skills()
        
        # Get Tools
        tools = get_langchain_tools()
        
        # Create the LangGraph agent
        self.agent = create_react_agent(llm, tools, state_modifier=system_prompt)

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
        import uuid
        
        # Convert incoming messages to LangGraph format
        messages = self.prep_msgs_for_llm([i.model_dump() for i in request.input])
        
        # Run the agent (LangGraph handles the Thought/Action/Observation loop)
        result = self.agent.invoke({"messages": messages})
        
        # Extract the final message
        final_message = result["messages"][-1].content
        
        # Return standard MLflow ResponsesAgentResponse
        output_item = self.create_text_output_item(text=final_message, id=str(uuid.uuid4()))
        return mlflow.types.responses.ResponsesAgentResponse(output=[output_item])

def log_agent_model():
    """
    Log the ResponsesAgent model to MLflow Unity Catalog.
    """
    # MLflow ResponsesAgent handles signature inference automatically
    with mlflow.start_run() as run:
        # We specify our custom wrapper class
        model_info = mlflow.pyfunc.log_model(
            artifact_path="agent",
            python_model=SupplyChainLangGraphAgent(),
            registered_model_name=MODEL_NAME,
            pip_requirements=[
                "mlflow==3.10.1", 
                "pandas==2.2.0", 
                "databricks-sdk==0.102.0", 
                "openai==1.14.3",
                "langchain==0.1.16",
                "langchain-core==0.1.45",
                "langchain-openai==0.1.3",
                "langgraph==0.0.39"
            ],
            code_paths=["backend"]
        )
        print(f"Logged LangGraph ResponsesAgent successfully to UC. Version: {model_info.registered_model_version}")
        return model_info.registered_model_version

if __name__ == "__main__":
    pass
