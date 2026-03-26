#!/bin/bash
set -e

# Prevent MSYS (Git Bash on Windows) from converting Databricks workspace paths to local Windows paths
export MSYS_NO_PATHCONV=1

# Supply Chain Agent - Databricks Apps Deployment Script
# 
# Usage:
#   ./deploy_app.sh

echo "🚀 Starting Databricks App Deployment Process..."

# Prompt for profile if not set in environment
if [[ -z "${DATABRICKS_PROFILE}" ]]; then
    echo "Available Databricks profiles:"
    databricks auth profiles 2>/dev/null | grep -v 'Warning' || cat ~/.databrickscfg | grep '\[' | tr -d '[]' | sed 's/^/  - /'
    echo ""
    echo "Please enter the Databricks CLI profile to use (default: DEFAULT):"
    read -p "> " input_profile
    export DATABRICKS_PROFILE=${input_profile:-"DEFAULT"}
fi

export APP_NAME=${APP_NAME:-"supply-chain-agent"}

echo "----------------------------------------"
echo "Deployment Configuration:"
echo "Profile:         $DATABRICKS_PROFILE"
echo "App Name:        $APP_NAME"
echo "----------------------------------------"

echo "🎨 Building React frontend..."
cd frontend
npm run build
cd ..

echo "📦 Syncing code to Databricks Workspace..."
# Create a hidden target folder in user's workspace
USER_EMAIL=$(databricks current-user me --profile $DATABRICKS_PROFILE | grep userName | cut -d '"' -f 4)
TARGET_PATH="/Workspace/Users/$USER_EMAIL/$APP_NAME-code"

echo "Target path: $TARGET_PATH"
# Using databricks sync to rapidly upload code. It ignores paths in .gitignore automatically
databricks sync . $TARGET_PATH --profile $DATABRICKS_PROFILE \
  --exclude node_modules \
  --exclude .venv \
  --exclude __pycache__ \
  --exclude .git \
  --exclude frontend/src \
  --exclude frontend/public \
  --exclude .DS_Store

echo "🏗️ Checking if App exists..."
if databricks apps get $APP_NAME --profile $DATABRICKS_PROFILE > /dev/null 2>&1; then
    echo "App '$APP_NAME' already exists. Updating..."
else
    echo "Creating new Databricks App '$APP_NAME'..."
    databricks apps create $APP_NAME --profile $DATABRICKS_PROFILE
    
    # Wait for the app to be created and compute assigned
    echo "Waiting for app environment to be provisioned (this can take 2-3 minutes)..."
    sleep 30
fi

echo "🚀 Deploying to Databricks Apps..."
databricks apps deploy $APP_NAME --source-code-path $TARGET_PATH --profile $DATABRICKS_PROFILE

echo ""
echo "✅ Deployment initiated!"
echo "Get the URL of your app with:"
echo "  databricks apps get $APP_NAME --profile $DATABRICKS_PROFILE"
echo ""
echo "To view live streaming logs, append /logz to your App URL!"
