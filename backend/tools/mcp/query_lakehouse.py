import os
import time
from databricks.sdk import WorkspaceClient

def query_lakehouse(sql_query: str) -> str:
    """
    Execute a read-only SQL query against the Databricks Lakehouse.
    Use this tool to answer general questions about the data that aren't covered by specific tools like get_inventory.
    For example, if asked 'What BUs are in the safety stock table?', you can query SELECT DISTINCT business_unit FROM taylor_hanson_build_catalog.supply_chain_schema.safety_stock.
    """
    try:
        w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))
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
