import os
import time
import random
from databricks.sdk import WorkspaceClient

def draft_purchase_order(sku: str, quantity: int) -> str:
    """
    Draft a purchase order for a SKU.
    Use this when asked to create or draft a new PO.
    """
    try:
        w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))
    except:
        return "Error: Could not connect to Databricks."
        
    catalog_schema = os.getenv("CATALOG_SCHEMA", "taylor_hanson_build_catalog.supply_chain_schema")
    po_id = f"PO-{random.randint(100000, 999999)}"
    
    # We execute an INSERT statement using the same logic as query_lakehouse
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
        
    sql_query = f"INSERT INTO {catalog_schema}.purchase_orders (po_id, sku, supplier_id, quantity, status, expected_date) VALUES ('{po_id}', '{sku}', 'UNKNOWN', {quantity}, 'draft', current_date() + INTERVAL 14 DAYS)"
    
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
            return f"Successfully drafted PO {po_id} for {sku} with quantity {quantity}."
        return f"SQL Failed: {status.error.message}"
    except Exception as e:
        return f"Error executing query: {str(e)}"
