import os
import time
import random
from datetime import datetime, timedelta
from databricks.sdk import WorkspaceClient

def wait_for_statement(w: WorkspaceClient, statement_id: str):
    while True:
        status = w.statement_execution.get_statement(statement_id).status
        if status.state.value in ["SUCCEEDED", "FAILED", "CANCELED", "CLOSED"]:
            if status.state.value != "SUCCEEDED":
                raise Exception(f"Statement failed: {status.error.message}")
            return
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
        print(f"No running warehouse found. Using {warehouses[0].name} ({warehouse_id}).")
    else:
        print(f"Using warehouse: {warehouse_id}")

    # Use the catalog and schema configured in the workspace setup
    schema_name = "taylor_hanson_build_catalog.supply_chain_schema"
    
    # Clean tables first
    print("Truncating tables...")
    run_sql(w, warehouse_id, f"TRUNCATE TABLE {schema_name}.inventory")
    run_sql(w, warehouse_id, f"TRUNCATE TABLE {schema_name}.suppliers")
    run_sql(w, warehouse_id, f"TRUNCATE TABLE {schema_name}.purchase_orders")
    run_sql(w, warehouse_id, f"TRUNCATE TABLE {schema_name}.safety_stock")

    # Generate Suppliers
    print("Generating suppliers...")
    supplier_ids = []
    suppliers_values = []
    company_prefixes = ["Acme", "Global", "Apex", "Zenith", "Pinnacle", "Quantum", "Nexus", "Summit", "Vanguard", "Horizon"]
    company_suffixes = ["Corp", "Inc", "Logistics", "Manufacturing", "Industries", "Group", "Solutions", "Dynamics", "Enterprises", "Systems"]
    for i in range(10):
        sup_id = f"SUP-{1000+i}"
        supplier_ids.append(sup_id)
        name = f"{random.choice(company_prefixes)} {random.choice(company_suffixes)}"
        lead_time = random.randint(3, 30)
        score = round(random.uniform(0.7, 0.99), 2)
        suppliers_values.append(f"('{sup_id}', '{name}', {lead_time}, {score})")
    
    # Generate Inventory
    print("Generating inventory...")
    skus = []
    inventory_values = []
    warehouses_list = ['WH-EAST', 'WH-WEST', 'WH-CENTRAL', 'WH-SOUTH', 'WH-NORTH']
    for i in range(50):
        sku = f"SKU-{random.randint(10000, 99999)}"
        skus.append(sku)
        wh = random.choice(warehouses_list)
        qty = random.randint(5, 500)
        reorder = random.randint(20, 100)
        inventory_values.append(f"('{sku}', '{wh}', {qty}, {reorder})")
        
    # Generate Purchase Orders
    print("Generating purchase orders...")
    po_values = []
    statuses = ['draft', 'submitted', 'approved', 'shipped', 'delivered', 'cancelled']
    for i in range(30):
        po_id = f"PO-{random.randint(100000, 999999)}"
        sku = random.choice(skus)
        sup = random.choice(supplier_ids)
        qty = random.randint(50, 1000)
        status = random.choice(statuses)
        date = (datetime.now() + timedelta(days=random.randint(1, 60))).strftime("%Y-%m-%d")
        po_values.append(f"('{po_id}', '{sku}', '{sup}', {qty}, '{status}', '{date}')")
        
    # Generate Safety Stock
    print("Generating safety stock...")
    ss_values = []
    bus = ['Retail', 'Wholesale', 'E-Commerce', 'B2B', 'Direct']
    for sku in skus:
        bu = random.choice(bus)
        min_stock = random.randint(10, 50)
        max_stock = min_stock + random.randint(50, 200)
        last_updated = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d %H:%M:%S")
        ss_values.append(f"('{sku}', '{bu}', {min_stock}, {max_stock}, '{last_updated}')")
        
    # Insert chunks
    def chunk_list(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    print("Inserting suppliers...")
    for chunk in chunk_list(suppliers_values, 100):
        run_sql(w, warehouse_id, f"INSERT INTO {schema_name}.suppliers VALUES {','.join(chunk)}")
        
    print("Inserting inventory...")
    for chunk in chunk_list(inventory_values, 100):
        run_sql(w, warehouse_id, f"INSERT INTO {schema_name}.inventory VALUES {','.join(chunk)}")
        
    print("Inserting purchase orders...")
    for chunk in chunk_list(po_values, 100):
        run_sql(w, warehouse_id, f"INSERT INTO {schema_name}.purchase_orders VALUES {','.join(chunk)}")
        
    print("Inserting safety stock...")
    for chunk in chunk_list(ss_values, 100):
        run_sql(w, warehouse_id, f"INSERT INTO {schema_name}.safety_stock VALUES {','.join(chunk)}")
        
    print("Successfully seeded all tables with random data!")

if __name__ == "__main__":
    main()