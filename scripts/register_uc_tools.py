import os
import requests
import time

def register_uc_tools():
    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")
    
    if not host or not token:
        # Try to get from CLI if not set
        import subprocess
        import json
        try:
            profile = os.environ.get("DATABRICKS_PROFILE", "myenv")
            host_out = subprocess.check_output(f"databricks auth describe --profile {profile} | grep 'host:' | awk '{{print $3}}'", shell=True)
            host = host_out.decode('utf-8').strip()
            token_out = subprocess.check_output(f"databricks auth token --profile {profile}", shell=True)
            token = json.loads(token_out.decode('utf-8')).get("access_token")
        except Exception as e:
            print(f"Error getting auth from CLI: {e}")
            return

    schema = "taylor_hanson_build_catalog.supply_chain_schema"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Get warehouse
    resp = requests.get(f"{host}/api/2.0/sql/warehouses", headers=headers)
    warehouses = resp.json().get("warehouses", [])
    wh_id = next((wh["id"] for wh in warehouses if wh["state"] in ['RUNNING', 'STARTING']), None)
    if not wh_id and warehouses: wh_id = warehouses[0]["id"]

    def execute_sql(sql):
        payload = {
            "statement": sql,
            "warehouse_id": wh_id,
            "wait_timeout": "30s"
        }
        resp = requests.post(f"{host}/api/2.0/sql/statements", headers=headers, json=payload)
        res = resp.json()
        while res.get("status", {}).get("state") in ["PENDING", "RUNNING"]:
            time.sleep(2)
            resp = requests.get(f"{host}/api/2.0/sql/statements/{res['statement_id']}", headers=headers)
            res = resp.json()
        if res.get("status", {}).get("state") != "SUCCEEDED":
            raise Exception(res.get("status", {}).get("error", {}).get("message", "Unknown error"))

    print(f"Registering UC tools in {schema}...")

    sql_get_inventory = f"""
    CREATE OR REPLACE FUNCTION {schema}.get_inventory(query_sku STRING)
    RETURNS STRING
    LANGUAGE PYTHON
    COMMENT 'Get inventory level for a SKU from Unity Catalog. Use this when asked to check stock or inventory.'
    AS $$
        return f"Inventory for {{query_sku}} is 150 units."
    $$
    """

    sql_manage_safety_stock = f"""
    CREATE OR REPLACE FUNCTION {schema}.manage_safety_stock(instruction STRING, file_name STRING, dry_run BOOLEAN, user_confirmation STRING)
    RETURNS STRING
    LANGUAGE PYTHON
    COMMENT 'Manage the safety_stock table. Set dry_run=True first. Once approved, set dry_run=False and provide exact user_confirmation.'
    AS $$
        if not file_name and not instruction:
            return "Error: You must provide either a file_name or an instruction."
            
        if not dry_run and not user_confirmation:
            return "Error: Human-in-the-Loop enforcement. You must provide the exact text of the user's approval in the 'user_confirmation' parameter when dry_run=False."
            
        if dry_run:
            return f"DRY RUN: Would apply instruction '{{instruction}}' or process file '{{file_name}}'. Please ask user for approval."
        else:
            return f"SUCCESS: Applied instruction with user confirmation: '{{user_confirmation}}'."
    $$
    """

    execute_sql(sql_get_inventory)
    print("Registered get_inventory")
    execute_sql(sql_manage_safety_stock)
    print("Registered manage_safety_stock")
    print("Successfully registered UC tools!")

if __name__ == "__main__":
    register_uc_tools()
