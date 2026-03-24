#!/bin/bash
set -e

# Supply Chain Agent Deployment Script
# 
# This script deploys the agent to a Databricks environment.
# It assumes you already have a target Unity Catalog and Schema created.
#
# Usage:
#   ./deploy.sh
#
# You can override defaults using environment variables:
#   CATALOG_SCHEMA="my_catalog.my_schema" ./deploy.sh

echo "🚀 Starting Deployment Process..."

# Default environment variables
export DATABRICKS_PROFILE=${DATABRICKS_PROFILE:-"myenv"}
export CATALOG_SCHEMA=${CATALOG_SCHEMA:-"taylor_hanson_build_catalog.supply_chain_schema"}
export MODEL_NAME=${MODEL_NAME:-"${CATALOG_SCHEMA}.agent_v1"}
export AGENT_ENDPOINT_NAME=${AGENT_ENDPOINT_NAME:-"supply_chain_agent_endpoint"}
export LLM_MODEL_NAME=${LLM_MODEL_NAME:-"databricks-claude-3-7-sonnet"}

echo "----------------------------------------"
echo "Deployment Configuration:"
echo "Profile:         $DATABRICKS_PROFILE"
echo "Catalog.Schema:  $CATALOG_SCHEMA"
echo "Model Name:      $MODEL_NAME"
echo "Endpoint Name:   $AGENT_ENDPOINT_NAME"
echo "LLM Model:       $LLM_MODEL_NAME"
echo "----------------------------------------"

echo "📦 Setting up Python environment..."
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt > /dev/null

echo "📦 Setting up Frontend environment..."
cd frontend
npm install > /dev/null
npm run build
cd ..

echo "🚀 Logging & Deploying Agent to Databricks Model Serving..."
# This script registers the MLflow model to UC and creates/updates the serving endpoint
python scripts/deploy_agent.py

echo "✅ Deployment initiated!"
echo "Check the Databricks UI to monitor the endpoint provisioning status."
echo "Once the endpoint is ready, you can start the application locally using:"
echo "  ./start.sh"
