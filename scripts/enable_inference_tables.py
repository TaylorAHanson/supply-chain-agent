import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput, TrafficConfig, AutoCaptureConfigInput

def enable_inference_tables():
    """
    Enables Inference Tables for the deployed AI Gateway route.
    This fulfills the 'Set up Inference Tables' step of the North Star Migration.
    """
    try:
        from backend.agent.config import CATALOG_SCHEMA
    except ImportError:
        CATALOG_SCHEMA = os.getenv("CATALOG_SCHEMA", "taylor_hanson_build_catalog.supply_chain_schema")
        
    w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE"))
    
    endpoint_name = "supply_chain_agent_endpoint"
    catalog, schema = CATALOG_SCHEMA.split(".")
    
    # Check if endpoint exists
    endpoints = [e.name for e in w.serving_endpoints.list()]
    
    if endpoint_name not in endpoints:
        print(f"Error: Endpoint '{endpoint_name}' does not exist. Please run create_ab_test_route.py first.")
        return
        
    print(f"Enabling Inference Tables for '{endpoint_name}' into {catalog}.{schema}.agent_payload_logs...")
    
    # We update the endpoint to include the auto_capture_config
    endpoint = w.serving_endpoints.get(endpoint_name)
    
    # Create the auto capture config
    auto_capture_config = AutoCaptureConfigInput(
        catalog_name=catalog,
        schema_name=schema,
        table_name_prefix="agent_payload_logs"
    )
    
    # Update the endpoint
    w.serving_endpoints.update_config(
        name=endpoint_name,
        served_entities=endpoint.config.served_entities,
        traffic_config=endpoint.config.traffic_config,
        auto_capture_config=auto_capture_config
    )
    
    print("Inference Tables enabled successfully!")

if __name__ == "__main__":
    enable_inference_tables()
