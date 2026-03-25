# Databricks notebook source
# MAGIC %md
# MAGIC # Deploy Supply Chain Agent
# MAGIC This notebook installs the necessary dependencies and runs the deployment script from within the Databricks Workspace compute environment. This bypasses corporate proxy timeouts and significantly speeds up MLflow artifact uploads.

# COMMAND ----------

# MAGIC %pip install -r requirements.txt

# COMMAND ----------

import sys
import os

# Add the current directory (the synced folder) to the Python path
# This ensures that the 'backend' package can be imported properly by the script
sys.path.append(os.getcwd())

# COMMAND ----------

# Run the deployment script
# MAGIC %run ./scripts/deploy_agent.py
