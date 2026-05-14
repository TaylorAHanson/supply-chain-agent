CREATE OR REPLACE FUNCTION taylor_hanson_build_catalog.supply_chain_schema.get_inventory(query_sku STRING)
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Get inventory level for a SKU from Unity Catalog. Use this when asked to check stock or inventory.'
AS $$
    # In a real UC function, this would query the local tables
    return f"Inventory for {query_sku} is 150 units."
$$;

CREATE OR REPLACE FUNCTION taylor_hanson_build_catalog.supply_chain_schema.manage_safety_stock(instruction STRING, file_name STRING, dry_run BOOLEAN, user_confirmation STRING)
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Manage the safety_stock table. Set dry_run=True first. Once approved, set dry_run=False and provide exact user_confirmation.'
AS $$
    if not file_name and not instruction:
        return "Error: You must provide either a file_name or an instruction."
        
    if not dry_run and not user_confirmation:
        return "Error: Human-in-the-Loop enforcement. You must provide the exact text of the user's approval in the 'user_confirmation' parameter when dry_run=False."
        
    if dry_run:
        return f"DRY RUN: Would apply instruction '{instruction}' or process file '{file_name}'. Please ask user for approval."
    else:
        return f"SUCCESS: Applied instruction with user confirmation: '{user_confirmation}'."
$$;
