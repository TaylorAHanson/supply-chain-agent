import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

os.environ["DATABRICKS_HOST"] = "https://example.cloud.databricks.com"
os.environ["DATABRICKS_CLIENT_ID"] = "dummy-client-id"
os.environ["DATABRICKS_CLIENT_SECRET"] = "dummy-client-secret"

try:
    c = Config(host=os.environ["DATABRICKS_HOST"], token="dummy-token", client_id=None, client_secret=None)
    c.authenticate()
    print("Success with None")
except Exception as e:
    print("Error with None:", e)

try:
    c = Config(host=os.environ["DATABRICKS_HOST"], token="dummy-token", auth_type="pat")
    c.authenticate()
    print("Success with pat")
except Exception as e:
    print("Error with pat:", e)

try:
    c = Config(host=os.environ["DATABRICKS_HOST"], token="dummy-token", credentials_provider=lambda cfg: lambda: {"Authorization": f"Bearer dummy-token"})
    c.authenticate()
    print("Success with provider")
except Exception as e:
    print("Error with provider:", e)

