import os

# Local Development Defaults
# In production, these are injected by Databricks Apps via app.yaml
CATALOG_SCHEMA = os.getenv("CATALOG_SCHEMA", "taylor_hanson_build_catalog.supply_chain_schema")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "databricks-claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "16384"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))