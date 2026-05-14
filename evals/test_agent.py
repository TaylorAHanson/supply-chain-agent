import os
import pandas as pd
import mlflow
from backend.agent.model import SupplyChainLangGraphAgent

def test_agent_evaluation():
    """
    Run an evaluation suite against the SupplyChainLangGraphAgent using MLflow Evaluate.
    This simulates a CI/CD check for the agent's performance.
    """
    
    # 1. Define evaluation dataset
    eval_data = pd.DataFrame(
        {
            "request": [
                "What is the current inventory for SKU-123?",
                "Can you draft a purchase order for 50 units of SKU-456?",
                "Who is the supplier for SKU-789?"
            ],
            "expected_response": [
                "The current inventory for SKU-123 is",
                "I have drafted a purchase order",
                "The supplier for SKU-789 is"
            ],
        }
    )

    # 2. Initialize the agent
    agent = SupplyChainLangGraphAgent()
    agent.load_context(None)
    
    # 3. Define a wrapper function for MLflow evaluate
    def model_wrapper(inputs):
        responses = []
        for req in inputs:
            # Construct the request dictionary matching MLflow ResponsesAgent schema
            from mlflow.types.responses import ResponsesAgentRequest
            
            agent_req = ResponsesAgentRequest(
                input=[{"role": "user", "content": req}],
                custom_inputs={"session_id": "eval-session"}
            )
            
            # Get the full response
            res = agent.predict(agent_req)
            
            # Extract text from response
            text_output = ""
            for item in res.output:
                if hasattr(item, "content") and isinstance(item.content, list):
                    for content_item in item.content:
                        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                            text_output += content_item.get("text", "")
            
            responses.append(text_output)
            
        return responses

    # 4. Run evaluation
    with mlflow.start_run(run_name="supply_chain_agent_eval"):
        results = mlflow.evaluate(
            model=model_wrapper,
            data=eval_data,
            model_type="question-answering",
            targets="expected_response",
            evaluators="default",
            extra_metrics=[
                mlflow.metrics.genai.answer_similarity(),
                mlflow.metrics.genai.answer_relevance()
            ]
        )
        
        print("Evaluation Results:")
        print(results.metrics)
        
        # Save results to a CSV for inspection
        results.tables["eval_results_table"].to_csv("evals/eval_results.csv", index=False)
        print("Detailed results saved to evals/eval_results.csv")

if __name__ == "__main__":
    test_agent_evaluation()
