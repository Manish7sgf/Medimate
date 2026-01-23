# MediMate Pro - PowerShell Quick Start Script

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MediMate Pro - Starting Application" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectDir = "c:\Users\manis\Desktop\New-PRO\medimate"

# Change to project directory
Set-Location -Path $projectDir

# Check if backend_service.py exists
if (-not (Test-Path "backend_service.py")) {
    Write-Host "ERROR: backend_service.py not found!" -ForegroundColor Red
    Write-Host "Make sure you run this script from: $projectDir" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[1/3] Checking dependencies..." -ForegroundColor Yellow
Write-Host ""

# Check if medimate.db exists
if (-not (Test-Path "medimate.db")) {
    Write-Host "  ℹ️  medimate.db will be created on first run" -ForegroundColor Gray
}

# Check if model directory exists
if (-not (Test-Path "medimate-disease-model")) {
    Write-Host "  ⚠️  WARNING: medimate-disease-model folder not found!" -ForegroundColor Yellow
    Write-Host "  This folder is required for ML predictions." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/3] Starting FastAPI Backend..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Backend URL: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Expected startup messages:" -ForegroundColor Gray
Write-Host "  - 'Database ready.'" -ForegroundColor Gray
Write-Host "  - 'ML Model loaded successfully!'" -ForegroundColor Gray
Write-Host ""

# Start backend in a new PowerShell window
$backendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$projectDir'; uvicorn backend_service:app --reload --port 8000" -PassThru -WindowStyle Normal

# Wait for backend to start
Write-Host "Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 6

Write-Host "[3/3] Opening Frontend in Browser..." -ForegroundColor Yellow
Write-Host ""

# Open the HTML file
Start-Process -FilePath "$projectDir\index.html"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Application Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "✅ Frontend: Opening in your default browser" -ForegroundColor Green
Write-Host "✅ Backend: Running on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "✅ Database: medimate.db (will be created if not exists)" -ForegroundColor Green
Write-Host ""
Write-Host "📝 NEXT STEPS:" -ForegroundColor Cyan
Write-Host "  1. Backend window will open - DO NOT CLOSE IT" -ForegroundColor White
Write-Host "  2. Wait for 'ML Model loaded successfully!' message" -ForegroundColor White
Write-Host "  3. Browser should open with login page" -ForegroundColor White
Write-Host "  4. Click 'Register' tab to create test account" -ForegroundColor White
Write-Host "  5. Use username: testuser123, password: Test123!" -ForegroundColor White
Write-Host "  6. Login and start testing the application" -ForegroundColor White
Write-Host ""
Write-Host "📖 For detailed testing guide, see: COMPLETE_TEST_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "🐛 Troubleshooting:" -ForegroundColor Yellow
Write-Host "  - If backend doesn't start, check Python/pip installation" -ForegroundColor Gray
Write-Host "  - If 'ML Model not loaded', verify model folder exists" -ForegroundColor Gray
Write-Host "  - If frontend doesn't open, manually open index.html in browser" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to exit this window (backend will keep running)"
