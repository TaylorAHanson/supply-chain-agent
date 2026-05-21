#!/bin/bash

echo "🚀 Starting Supply Chain Agent local development environment..."

# Prompt for profile if not set in environment
if [[ -z "${DATABRICKS_PROFILE}" ]]; then
    echo "Available Databricks profiles:"
    databricks auth profiles 2>/dev/null | grep -v 'Warning' || cat ~/.databrickscfg | grep '\[' | tr -d '[]' | sed 's/^/  - /'
    echo ""
    echo "Please enter the Databricks CLI profile to use (default: myenv):"
    read -p "> " input_profile
    export DATABRICKS_PROFILE=${input_profile:-"myenv"}
fi

echo "Using profile: $DATABRICKS_PROFILE"

# Set up cleanup on exit
trap cleanup INT TERM EXIT

function cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [[ -n "$BACKEND_PID" ]]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [[ -n "$FRONTEND_PID" ]]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit 0
}

# Activate virtual environment
if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
elif [[ -f ".venv/Scripts/activate" ]]; then
    source .venv/Scripts/activate
else
    echo "⚠️  Warning: Could not find virtual environment. Falling back to system Python."
fi

# Ensure dependencies are installed (optional, but helpful for dev)
if [[ ! -d "node_modules" ]]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

echo "🐍 Starting FastAPI backend on port 8000..."
# We use Python module execution to ensure the path is right
python -m uvicorn backend.app:app --reload --port 8000 &
BACKEND_PID=$!

echo "⚛️  Starting React frontend..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Local development environment is running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both services."

# Wait forever (until interrupted)
wait
