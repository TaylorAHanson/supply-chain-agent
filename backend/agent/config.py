import os

# Configuration for Databricks Agent Endpoint
AGENT_ENDPOINT_NAME = os.getenv("AGENT_ENDPOINT_NAME", "supply_chain_agent_v2_endpoint")
MODEL_NAME = os.getenv("MODEL_NAME", "taylor_hanson_build_catalog.supply_chain_schema.agent_v1")
CATALOG_SCHEMA = os.getenv("CATALOG_SCHEMA", "taylor_hanson_build_catalog.supply_chain_schema")
LLM_ENDPOINT_URL = os.getenv("LLM_ENDPOINT_URL", "/api/2.0/serving-endpoints/databricks-claude-sonnet-4-6/invocations")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "databricks-claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "01f127a4bd121688a25e50c1ffe93651")