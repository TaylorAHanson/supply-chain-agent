import os
from databricks.sdk import WorkspaceClient

profile = os.getenv("DATABRICKS_PROFILE", "myenv")
w = WorkspaceClient(profile=profile)

query = """
SELECT routine_catalog, routine_schema, routine_name 
FROM system.information_schema.routines 
WHERE routine_type = 'FUNCTION' AND routine_catalog != 'system'
"""

try:
    response = w.statement_execution.execute_statement(
        statement=query,
        warehouse_id="238e4114cdfd555f",
        wait_timeout="10s"
    )
    print(response.status.state)
    
    if response.status.state.value == 'SUCCEEDED':
        for row in response.result.data_array:
            print(row)
    else:
        print(f"Failed: {response.status.state}")
except Exception as e:
    print(f"Error: {e}")
