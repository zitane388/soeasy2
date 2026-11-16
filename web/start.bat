@echo off
REM Soeasy2 Web UI Startup Script (Windows)

echo.
echo Starting Soeasy2 Web Interface...
echo.

REM Check if we're in the web directory
if not exist "backend" (
    echo Error: Please run this script from the web/ directory
    exit /b 1
)
if not exist "frontend" (
    echo Error: Please run this script from the web/ directory
    exit /b 1
)

REM Start Backend
echo Starting Flask Backend (port 5000)...
cd backend
start "Flask Backend" cmd /k "python app.py"
cd ..

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start Frontend
echo.
echo Starting React Frontend (port 5173)...
cd frontend
start "React Frontend" cmd /k "npm run dev"
cd ..

echo.
echo Both servers started!
echo.
echo Access the app at: http://localhost:5173
echo.
echo Press any key to exit...
pause >nul
