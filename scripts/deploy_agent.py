import os
import mlflow
from databricks import agents
from databricks.sdk import WorkspaceClient
from backend.agent.config import MODEL_NAME, CATALOG_SCHEMA, AGENT_ENDPOINT_NAME
from backend.agent.model import log_agent_model

def main():
    import os
    profile = os.environ.get("DATABRICKS_PROFILE", "myenv")
    
    # Force authentication using the configured profile for agents.deploy
    w = WorkspaceClient(profile=profile)
    auth_headers = w.config.authenticate()
    os.environ["DATABRICKS_HOST"] = w.config.host
    if isinstance(auth_headers, dict) and "Authorization" in auth_headers:
        os.environ["DATABRICKS_TOKEN"] = auth_headers["Authorization"].replace("Bearer ", "")
    elif w.config.token:
        os.environ["DATABRICKS_TOKEN"] = w.config.token

    print(f"Logging agent model to UC: {MODEL_NAME}")
    
    # 1. Log the model
    # Note: MLflow requires the registry_uri to be set to databricks-uc
    mlflow.set_tracking_uri(f"databricks://{profile}")
    mlflow.set_registry_uri(f"databricks-uc://{profile}")
    
    # Configure MLflow HTTP timeout (prevent 5 minute hangs)
    os.environ["MLFLOW_HTTP_REQUEST_TIMEOUT"] = "60"
    
    # We will log without hitting AWS S3 directly for artifacts if the connection is slow.
    # MLflow can try to upload files directly to the storage backend (S3/ADLS) from your machine.
    # We can ask MLflow to route it through the Databricks control plane instead if it hangs.
    # The default upload is sometimes blocked by corporate network egress rules because it hits cloud storage URLs directly.
    os.environ["MLFLOW_ENABLE_MULTIPART_UPLOAD"] = "false"
    os.environ["DATABRICKS_DISABLE_DIRECT_UPLOAD"] = "true"
    
    # Set the experiment
    import json
    import subprocess
    # Find user email via databricks CLI to use as experiment path
    user_email = subprocess.check_output(
        ["databricks", "current-user", "me", "--profile", profile], 
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
