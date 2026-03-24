#!/usr/bin/env bash

# Set Databricks profile (defaults to myenv if not already set)
export DATABRICKS_PROFILE=${DATABRICKS_PROFILE:-myenv}

echo "🚀 Starting Supply Chain Agent..."

# Usage Note:
# To run the agent locally (faster dev loop without deploying to Model Serving):
#   LOCAL_MODE=true ./start.sh

# Kill any existing processes on ports 8000 and 5173
echo "🧹 Cleaning up ports 8000 and 5173..."
if command -v lsof &> /dev/null; then
    # macOS/Linux
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    lsof -ti:5173 | xargs kill -9 2>/dev/null
elif command -v netstat &> /dev/null; then
    # Windows fallback
    netstat -ano | grep :8000 | awk '{print $5}' | xargs taskkill /F /PID 2>/dev/null
    netstat -ano | grep :5173 | awk '{print $5}' | xargs taskkill /F /PID 2>/dev/null
fi

# Create logs directory
mkdir -p logs

# Activate virtual environment (cross-platform compatible for Mac/Linux and Windows Git Bash)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "⚠️  Warning: Could not find virtual environment. Please run 'python -m venv .venv' first."
fi

# Start FastAPI backend in the background and log to file
echo "📦 Starting FastAPI backend on http://localhost:8000 (logging to logs/backend.log)..."
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Start React frontend in the background and log to file
echo "🎨 Starting React frontend on http://localhost:5173 (logging to logs/frontend.log)..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both servers are running!"
echo "👉 UI: http://localhost:5173"
echo "👉 API: http://localhost:8000/docs"
echo "👉 Logs: 'tail -f logs/backend.log' or 'tail -f logs/frontend.log'"
echo "Press Ctrl+C to stop both servers."

# Trap Ctrl+C (SIGINT) and SIGTERM to kill both background processes gracefully
trap "echo -e '\n🛑 Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# Wait for background processes to keep script running
wait $BACKEND_PID $FRONTEND_PID
