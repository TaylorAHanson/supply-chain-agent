import os
import mlflow
from databricks import agents
from databricks.sdk import WorkspaceClient
from backend.agent.config import MODEL_NAME, CATALOG_SCHEMA, AGENT_ENDPOINT_NAME
from backend.agent.model import log_agent_model

def main():
    # Force authentication using 'myenv' profile for agents.deploy
    w = WorkspaceClient(profile="myenv")
    auth_headers = w.config.authenticate()
    os.environ["DATABRICKS_HOST"] = w.config.host
    if isinstance(auth_headers, dict) and "Authorization" in auth_headers:
        os.environ["DATABRICKS_TOKEN"] = auth_headers["Authorization"].replace("Bearer ", "")
    elif w.config.token:
        os.environ["DATABRICKS_TOKEN"] = w.config.token

    print(f"Logging agent model to UC: {MODEL_NAME}")
    
    # 1. Log the model
    # Note: MLflow requires the registry_uri to be set to databricks-uc
    mlflow.set_tracking_uri("databricks://myenv")
    mlflow.set_registry_uri("databricks-uc://myenv")
    
    # Set the experiment
    import json
    import subprocess
    # Find user email via databricks CLI to use as experiment path
    user_email = subprocess.check_output(
        ["databricks", "current-user", "me", "--profile", "myenv"], 
        text=True
    ).strip()
    try:
        user_data = json.loads(user_email)
        user_email = user_data.get("userName", "unknown@example.com")
    except:
        pass
    
    experiment_path = f"/Users/{user_email}/supply_chain_agent"
    print(f"Setting MLflow experiment to {experiment_path}")
    mlflow.set_experiment(experiment_path)
    
    # Run the logging function which calls agents.mlflow.set_model
    latest_version = log_agent_model()
    
    print(f"Logged model {MODEL_NAME} version {latest_version}")

    # 2. Deploy to serving endpoint
    print(f"Deploying version {latest_version} to endpoint: {AGENT_ENDPOINT_NAME}")
    try:
        deploy_info = agents.deploy(
            model_name=MODEL_NAME,
            model_version=latest_version,
            endpoint_name=AGENT_ENDPOINT_NAME
        )
        print("Deploy info:", deploy_info)
    except Exception as e:
        print(f"Deployment failed or endpoint exists: {e}")
        # Could use databricks SDK to update the endpoint if it already exists,
        # but agents.deploy handles updates in recent versions.

if __name__ == "__main__":
    main()
