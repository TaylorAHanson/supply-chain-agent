#!/bin/bash

echo "🚀 Starting Supply Chain Agent local development environment..."

# Set up cleanup on exit
trap cleanup INT TERM EXIT

function cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ -n "$FRONTEND_PID" ]; then
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
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

echo "🐍 Starting FastAPI backend on port 8000..."
# We use Python module execution to ensure the path is right
python -m uvicorn backend.app:app --reload --port 8000 &
BACKEND_PID=$!

echo "⚛️  Starting React frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Local development environment is running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both services."

# Wait forever (until interrupted)
wait
