import os

# Configuration is environment-driven. In production these are injected by Databricks Apps via
# databricks.yml; for local development export them yourself (dev.sh sets sensible defaults, or
# copy .env.example). CATALOG_SCHEMA / SKILLS_VOLUME_PATH intentionally have no hard-coded default
# so the agent stays generic and not tied to any one workspace's catalog.
CATALOG_SCHEMA = os.getenv("CATALOG_SCHEMA", "")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "databricks-claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "16384"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))
SKILLS_VOLUME_PATH = os.getenv("SKILLS_VOLUME_PATH", "")
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")