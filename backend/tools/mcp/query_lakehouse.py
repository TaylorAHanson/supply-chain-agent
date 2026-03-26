import os
import time
from databricks.sdk import WorkspaceClient

def query_lakehouse(sql_query: str) -> str:
    """
    Execute a read-only SQL query against the Databricks Lakehouse.
    Use this tool to answer general questions about the data.
    IMPORTANT: You MUST use fully qualified table names (e.g., `catalog.schema.table_name`) in your SQL queries, 
    as the data could be located in various catalogs and schemas. If you do not know the correct catalog and schema, 
    either ask the user or use `SHOW CATALOGS` and query `system.information_schema.tables` to find the correct data.
    """
    try:
        w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE"))
    except:
        return "Error: Could not connect to Databricks."
        
    warehouses = list(w.warehouses.list())
    wh_id = None
    for wh in warehouses:
        if wh.state.name in ['RUNNING', 'STARTING']:
            wh_id = wh.id
            break
    if not wh_id and len(warehouses) > 0:
        wh_id = warehouses[0].id
        
    if not wh_id:
        return "Error: No SQL warehouse found."
        
    try:
        res = w.statement_execution.execute_statement(
            statement=sql_query,
            warehouse_id=wh_id,
            wait_timeout="0s"
        )
        
        stmt_id = res.statement_id
        while True:
            status = w.statement_execution.get_statement(stmt_id).status
            if status.state.value in ["SUCCEEDED", "FAILED", "CANCELED", "CLOSED"]:
                break
            time.sleep(1)
            
        if status.state.value == "SUCCEEDED":
            result = w.statement_execution.get_statement(stmt_id)
            if result.result and result.result.data_array:
                # Format the output as a simple string representation
                columns = [col.name for col in result.manifest.schema.columns] if result.manifest and result.manifest.schema else []
                output = f"Columns: {columns}\nData:\n"
                for row in result.result.data_array[:100]: # Limit to 100 rows for context limits
                    output += f"{row}\n"
                return output
            return "Query executed successfully but returned no data."
        return f"SQL Failed: {status.error.message}"
    except Exception as e:
        return f"Error executing query: {str(e)}"
