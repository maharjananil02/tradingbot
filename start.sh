#!/bin/bash

echo "Starting Backend API on port 8000..."
cd backend
# Free up port 8000 if it's already in use
lsof -ti :8000 | xargs kill -9 2>/dev/null
# Use the virtual environment's Python to run the backend in the background
../.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

echo "Starting Frontend Development Server..."
cd frontend
# Run the vite frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "========================================="
echo "Services are running!"
echo "Backend PID: $BACKEND_PID (http://localhost:8000)"
echo "Frontend PID: $FRONTEND_PID (http://localhost:3000)"
echo "Press Ctrl+C to stop both services."
echo "========================================="

# Trap Ctrl+C (SIGINT) to kill both the frontend and backend processes
trap "echo '\nStopping services...'; kill -9 $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT

# Wait indefinitely, keeping the script alive so the trap can catch Ctrl+C
wait $BACKEND_PID $FRONTEND_PID
