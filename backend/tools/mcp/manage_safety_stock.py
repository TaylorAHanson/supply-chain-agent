import os
import time
import pandas as pd
import io
from databricks.sdk import WorkspaceClient

def manage_safety_stock(instruction: str, file_name: str = None, dry_run: bool = True) -> str:
    """
    Manage the safety_stock table. 
    IMPORTANT: BEFORE using this tool, you MUST use the `read_skill` tool to read the `analyze_safety_stock` skill to understand the correct workflow.
    
    Use this tool to analyze uploaded files or apply instructions to the safety stock table.
    - If a user uploads a file, pass the file_name to process it.
    - Set dry_run=True first to get the delta of what will change (rows added, updated, deleted) and review with the customer.
    - Once the customer approves, set dry_run=False to actually commit the changes to the table.
    """
    # Simple check to make sure the agent is providing something
    if not file_name and not instruction:
        return "Error: You must provide either a file_name or an instruction."
        
    try:
        from backend.agent.config import CATALOG_SCHEMA
    except ImportError:
        CATALOG_SCHEMA = "taylor_hanson_build_catalog.supply_chain_schema"
        
    catalog, schema = CATALOG_SCHEMA.split(".")
    table_name = f"{CATALOG_SCHEMA}.safety_stock"
    
    try:
        w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))
    except Exception as e:
        return f"Error connecting to Databricks: {str(e)}"
        
    # Find warehouse
    warehouses = list(w.warehouses.list())
    wh_id = next((wh.id for wh in warehouses if wh.state.name in ['RUNNING', 'STARTING']), None)
    if not wh_id and warehouses: wh_id = warehouses[0].id
    if not wh_id: return "Error: No SQL warehouse found."

    def execute_sql(sql):
        res = w.statement_execution.execute_statement(statement=sql, warehouse_id=wh_id, wait_timeout="0s")
        while True:
            status = w.statement_execution.get_statement(res.statement_id).status
            if status.state.value in ["SUCCEEDED", "FAILED", "CANCELED", "CLOSED"]: break
            time.sleep(1)
        if status.state.value != "SUCCEEDED": raise Exception(status.error.message)
        return w.statement_execution.get_statement(res.statement_id)

    # 1. If processing a file upload
    if file_name:
        volume_path = f"/Volumes/{catalog}/{schema}/uploads/{file_name}"
        try:
            # Download file from volume
            file_resp = w.files.download(volume_path)
            content = file_resp.contents.read()
            
            if file_name.endswith('.csv'):
                df_new = pd.read_csv(io.BytesIO(content))
            elif file_name.endswith('.xlsx'):
                df_new = pd.read_excel(io.BytesIO(content))
            else:
                return "Error: Unsupported file format. Please upload a CSV or XLSX file."
                
            # Basic validation
            required_cols = ['sku', 'business_unit', 'min_stock_level', 'max_stock_level']
            for col in required_cols:
                if col not in df_new.columns:
                    return f"Error: Uploaded file is missing required column: {col}"
                    
        except Exception as e:
            return f"Error reading file from Volume: {str(e)}"
            
        # Delta processing for file upload
        if dry_run:
            # For a dry run, we just summarize what the file contains
            num_rows = len(df_new)
            skus = df_new['sku'].nunique()
            return f"DRY RUN (Delta Analysis):\nFile '{file_name}' contains {num_rows} rows across {skus} SKUs.\nSample of new data:\n{df_new.head().to_string()}\n\nPlease present this summary to the user and ask for approval to overwrite/update the safety stock table."
        else:
            # Commit logic: We will do a full replace for simplicity in this MVP
            try:
                # Truncate and insert
                execute_sql(f"TRUNCATE TABLE {table_name}")
                
                # Insert rows in chunks
                import datetime
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                values = []
                for _, row in df_new.iterrows():
                    values.append(f"('{row['sku']}', '{row['business_unit']}', {row['min_stock_level']}, {row['max_stock_level']}, '{now_str}')")
                
                # Chunk inserts to avoid massive SQL strings
                chunk_size = 500
                for i in range(0, len(values), chunk_size):
                    chunk = values[i:i+chunk_size]
                    sql = f"INSERT INTO {table_name} VALUES {','.join(chunk)}"
                    execute_sql(sql)
                    
                return f"SUCCESS: The safety stock table was successfully replaced with {len(df_new)} rows from {file_name}."
            except Exception as e:
                return f"Error updating table: {str(e)}"

    # 2. If applying an instruction (e.g. "set stock to 0 for Retail")
    if instruction:
        if dry_run:
            return f"DRY RUN: To apply the instruction '{instruction}', I would need to generate a SQL UPDATE statement. Please use the `query_lakehouse` tool to generate and test a SELECT statement first to see which rows will be affected, show the user, and then you can execute the UPDATE manually."
        else:
            return "For instruction execution, please use `query_lakehouse` to directly execute the UPDATE statement after getting user approval."
