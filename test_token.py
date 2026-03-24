import os
from databricks.sdk import WorkspaceClient
w = WorkspaceClient(profile="myenv")
headers = w.config.authenticate()
token = headers.get("Authorization", "").replace("Bearer ", "") if isinstance(headers, dict) else w.config.token
print("Token:", token[:10] + "..." if token else None)
