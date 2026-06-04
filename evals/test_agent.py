import os
import pandas as pd
import mlflow
from backend.agent.model import EDHAgent

def test_agent_evaluation():
    """
    Run an evaluation suite against the EDHAgent using MLflow Evaluate.
    This simulates a CI/CD check for the agent's performance.
    """
    
    # 1. Define evaluation dataset (generic data-assistant questions; customize per workspace)
    eval_data = pd.DataFrame(
        {
            "request": [
                "Which Unity Catalog catalogs can I access?",
                "How many rows are in the largest table you can see? Use SQL.",
                "List the Genie spaces available to me."
            ],
            "expected_response": [
                "A list of accessible catalogs",
                "A row count for the largest accessible table",
                "A list of available Genie spaces with their space ids"
            ],
        }
    )

    # 2. Initialize the agent
    agent = EDHAgent()
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
    with mlflow.start_run(run_name="edh_agent_eval"):
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
