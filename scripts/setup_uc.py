import os
import time
from databricks.sdk import WorkspaceClient

# Wait for a statement execution to complete
def wait_for_statement(w: WorkspaceClient, statement_id: str):
    while True:
        status = w.statement_execution.get_statement(statement_id).status
        if status.state.value in ["SUCCEEDED", "FAILED", "CANCELED", "CLOSED"]:
            if status.state.value != "SUCCEEDED":
                raise Exception(f"Statement failed: {status.error.message}")
            return
        print(f"Waiting for statement {statement_id} to finish (current state: {status.state})...")
        time.sleep(2)

def run_sql(w: WorkspaceClient, warehouse_id: str, sql: str):
    print(f"Executing: {sql[:50]}...")
    res = w.statement_execution.execute_statement(
        statement=sql,
        warehouse_id=warehouse_id,
        wait_timeout="0s"
    )
    if res.statement_id:
        wait_for_statement(w, res.statement_id)

def main():
    print("Connecting to Databricks...")
    w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))

    # Find a running or available SQL Warehouse
    print("Finding a SQL Warehouse...")
    warehouses = list(w.warehouses.list())
    if not warehouses:
        raise Exception("No SQL Warehouses found in the workspace.")
    
    warehouse_id = None
    for wh in warehouses:
        if wh.state.name in ['RUNNING', 'STARTING']:
            warehouse_id = wh.id
            break
            
    if not warehouse_id:
        warehouse_id = warehouses[0].id
        print(f"No running warehouse found. Using {warehouses[0].name} ({warehouse_id}). Note: It might take a few minutes to start.")
    else:
        print(f"Using warehouse: {warehouse_id}")

    schema_name = "taylor_hanson_build_catalog.supply_chain_schema"
    
    # 1. Create Schema
    run_sql(w, warehouse_id, f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
    
    # 1.b Create Volume for uploads
    run_sql(w, warehouse_id, f"CREATE VOLUME IF NOT EXISTS {schema_name}.uploads")
    
    # 2. Create Tables
    tables_sql = [
        f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.inventory (
            sku STRING,
            warehouse_id STRING,
            quantity_on_hand INT,
            reorder_point INT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.suppliers (
            supplier_id STRING,
            name STRING,
            avg_lead_time_days INT,
            reliability_score DOUBLE
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.purchase_orders (
            po_id STRING,
            sku STRING,
            supplier_id STRING,
            quantity INT,
            status STRING,
            expected_date STRING
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.safety_stock (
            sku STRING,
            business_unit STRING,
            min_stock_level INT,
            max_stock_level INT,
            last_updated TIMESTAMP
        )
        """
    ]
    
    for sql in tables_sql:
        run_sql(w, warehouse_id, sql)
        
    # 3. Dummy Data Seeding
    # Please run `python scripts/seed_data.py` to populate tables with fake data.


    # 4. Create UC Functions
    functions_sql = [
        f"""
        CREATE OR REPLACE FUNCTION {schema_name}.get_inventory(query_sku STRING)
        RETURNS TABLE (sku STRING, quantity_on_hand INT, reorder_point INT, warehouse_id STRING)
        RETURN SELECT sku, quantity_on_hand, reorder_point, warehouse_id FROM {schema_name}.inventory WHERE sku = query_sku
        """,
        f"""
        CREATE OR REPLACE FUNCTION {schema_name}.get_supplier_lead_times(query_supplier_id STRING)
        RETURNS TABLE (supplier_id STRING, avg_lead_time_days INT, reliability_score DOUBLE)
        RETURN SELECT supplier_id, avg_lead_time_days, reliability_score FROM {schema_name}.suppliers WHERE supplier_id = query_supplier_id
        """
    ]
    
    for sql in functions_sql:
        run_sql(w, warehouse_id, sql)

    print("Setup completed successfully!")

if __name__ == "__main__":
    main()
