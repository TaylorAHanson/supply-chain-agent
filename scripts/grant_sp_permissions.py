import os
import requests
import json
import subprocess

def grant_permissions():
    profile = os.environ.get("DATABRICKS_PROFILE", "myenv")
    try:
        host_out = subprocess.check_output(f"databricks auth describe --profile {profile} | grep 'host:' | awk '{{print $3}}'", shell=True)
        host = host_out.decode('utf-8').strip()
        token_out = subprocess.check_output(f"databricks auth token --profile {profile}", shell=True)
        token = json.loads(token_out.decode('utf-8')).get("access_token")
    except Exception as e:
        print(f"Error getting auth from CLI: {e}")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Find warehouse
    resp = requests.get(f"{host}/api/2.0/sql/warehouses", headers=headers)
    warehouses = resp.json().get("warehouses", [])
    wh_id = next((wh["id"] for wh in warehouses if wh["state"] in ['RUNNING', 'STARTING']), None)
    if not wh_id and warehouses: wh_id = warehouses[0]["id"]
    if not wh_id: 
        print("Error: No SQL warehouse found.")
        return

    def execute_sql(sql):
        payload = {
            "statement": sql,
            "warehouse_id": wh_id,
            "wait_timeout": "30s"
        }
        resp = requests.post(f"{host}/api/2.0/sql/statements", headers=headers, json=payload)
        res = resp.json()
        import time
        while res.get("status", {}).get("state") in ["PENDING", "RUNNING"]:
            time.sleep(2)
            resp = requests.get(f"{host}/api/2.0/sql/statements/{res['statement_id']}", headers=headers)
            res = resp.json()
        if res.get("status", {}).get("state") != "SUCCEEDED":
            print(f"Error executing SQL: {res.get('status', {}).get('error', {}).get('message', 'Unknown error')}")
        else:
            print("Success")

    sp_client_id = "fe4824e0-a251-4986-b8b4-2e36f3463c53"
    catalog = "taylor_hanson_build_catalog"
    schema = f"{catalog}.supply_chain_schema"
    
    print(f"Granting permissions to {sp_client_id}...")
    execute_sql(f"GRANT USE CATALOG ON CATALOG {catalog} TO `{sp_client_id}`")
    execute_sql(f"GRANT USE SCHEMA ON SCHEMA {schema} TO `{sp_client_id}`")
    execute_sql(f"GRANT EXECUTE ON SCHEMA {schema} TO `{sp_client_id}`")
    execute_sql(f"GRANT READ VOLUME ON VOLUME {schema}.skills TO `{sp_client_id}`")
    execute_sql(f"GRANT WRITE VOLUME ON VOLUME {schema}.uploads TO `{sp_client_id}`")

if __name__ == "__main__":
    grant_permissions()
