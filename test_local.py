import os
os.environ["LOCAL_MODE"] = "true"
os.environ["DATABRICKS_PROFILE"] = "myenv"

from backend.agent.model import SupplyChainLangGraphAgent
from mlflow.types.responses import ResponsesAgentRequest
import uuid

def test_local():
    agent = SupplyChainLangGraphAgent()
    agent.load_context(None)
    
    req = ResponsesAgentRequest(
        input=[{"role": "user", "content": "What is the capital of France?"}]
    )
    
    print("Sending request to agent...")
    try:
        response = agent.predict(req)
        print("Response received:", response)
        
        output_item = response.output[0]
        # Depending on mlflow's implementation, it might be a dict or a Pydantic object
        if hasattr(output_item, 'content'):
            content = output_item.content
            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                if hasattr(first_item, 'text'):
                    print("Text:", first_item.text)
                elif isinstance(first_item, dict):
                    print("Text:", first_item.get('text', ''))
            else:
                print("Text directly:", content)
        elif isinstance(output_item, dict):
            print("Dict Text:", output_item.get("content", [{}])[0].get("text"))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_local()
