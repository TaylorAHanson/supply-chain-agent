import os

# Configuration for Databricks Agent Endpoint
AGENT_ENDPOINT_NAME = os.getenv("AGENT_ENDPOINT_NAME", "supply_chain_agent_endpoint")
MODEL_NAME = os.getenv("MODEL_NAME", "taylor_hanson_build_catalog.supply_chain_schema.agent_v1")
CATALOG_SCHEMA = os.getenv("CATALOG_SCHEMA", "taylor_hanson_build_catalog.supply_chain_schema")
LLM_ENDPOINT_URL = os.getenv("LLM_ENDPOINT_URL", "/api/2.0/serving-endpoints/databricks-meta-llama-3-1-405b-instruct/invocations")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "databricks-meta-llama-3-1-405b-instruct")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))