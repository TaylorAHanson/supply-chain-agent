import os
import mlflow

profile = os.getenv("DATABRICKS_PROFILE", "myenv")
mlflow.set_tracking_uri(f"databricks://{profile}")

try:
    mlflow.set_experiment("/Shared/supply_chain_agent")
    print("Experiment set successfully!")
    
    with mlflow.start_run() as run:
        print(f"Started run: {run.info.run_id}")
        mlflow.log_param("test", "value")
        
    print("Trace test:")
    @mlflow.trace(name="test_trace")
    def my_func():
        return "hello"
        
    my_func()
    print("Trace logged successfully!")
except Exception as e:
    print(f"Error: {e}")
