import mlflow
from mlflow.tracking.client import MlflowClient

client = MlflowClient()
model_uri = "models:/taylor_hanson_build_catalog.supply_chain_schema.agent_v1/14"
path = client.download_artifacts(model_uri, "")
print(f"Downloaded to {path}")

import os
for root, dirs, files in os.walk(path):
    for f in files:
        print(os.path.join(root, f).replace(path, ""))
