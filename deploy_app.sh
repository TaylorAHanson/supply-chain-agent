#!/bin/bash
set -e

# Prevent MSYS (Git Bash on Windows) from converting Databricks workspace paths to local Windows paths
export MSYS_NO_PATHCONV=1

# Supply Chain Agent - Databricks Apps Deployment Script
# 
# Usage:
#   ./deploy_app.sh

echo "🚀 Starting Databricks App Deployment Process using Asset Bundles..."

echo "📦 Validating bundle..."
databricks bundle validate -t dev

echo "🚀 Deploying bundle to Databricks..."
databricks bundle deploy -t dev

echo "🏃 Running the app..."
databricks bundle run supply_chain_agent -t dev

echo ""
echo "✅ Deployment complete!"
echo "Get the URL of your app from the Databricks UI or by running:"
echo "  databricks apps get supply-chain-agent --profile $DATABRICKS_PROFILE"
echo ""
echo "To view live streaming logs, append /logz to your App URL!"
