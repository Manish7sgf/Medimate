@echo off
REM MediMate Pro - Quick Start Script

echo.
echo ========================================
echo   MediMate Pro - Starting Application
echo ========================================
echo.

REM Get the project directory
set PROJECT_DIR=c:\Users\manis\Desktop\New-PRO\medimate

REM Check if we're in the right directory
cd /d %PROJECT_DIR%

if not exist "backend_service.py" (
    echo ERROR: backend_service.py not found!
    echo Make sure you run this script from: %PROJECT_DIR%
    pause
    exit /b 1
)

echo [1/2] Starting FastAPI Backend...
echo.
echo Backend URL: http://127.0.0.1:8000
echo Press Ctrl+C in the backend window to stop it.
echo.
echo Expected messages:
echo   - "Database ready."
echo   - "ML Model loaded successfully!"
echo.

REM Start uvicorn in a new window
start "MediMate Backend" cmd /k "uvicorn backend_service:app --reload --port 8000"

REM Wait a few seconds for backend to start
timeout /t 5 /nobreak

echo.
echo [2/2] Opening Frontend...
echo.

REM Open the HTML file in default browser
start "" "%PROJECT_DIR%\index.html"

echo.
echo ========================================
echo     Application Started Successfully!
echo ========================================
echo.
echo Frontend: Opening in your default browser
echo Backend: Running on http://127.0.0.1:8000
echo.
echo NEXT STEPS:
echo 1. Wait for backend to fully load (5 seconds)
echo 2. You should see the login page in browser
echo 3. Click "Register" tab to create test account
echo 4. Use username: testuser123, password: Test123!
echo 5. Login and start testing!
echo.
echo For detailed testing guide, see: COMPLETE_TEST_GUIDE.md
echo.
pause
