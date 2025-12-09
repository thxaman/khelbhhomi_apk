# Quick Build Script for KhelBhoomi APK
# Run this script to rebuild your APK with camera fixes

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "KhelBhoomi APK Builder with Camera Fix" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Clean previous build
Write-Host "[1/3] Cleaning previous build..." -ForegroundColor Yellow
buildozer android clean

# Step 2: Build debug APK
Write-Host ""
Write-Host "[2/3] Building APK (this may take 10-20 minutes)..." -ForegroundColor Yellow
Write-Host "      Grab a coffee! ☕" -ForegroundColor Green
buildozer -v android debug

# Step 3: Check if build succeeded
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ BUILD SUCCESSFUL!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "APK Location: bin/khelbhoomi-0.1-debug.apk" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. Connect your Android device via USB" -ForegroundColor White
    Write-Host "2. Enable USB debugging on your device" -ForegroundColor White
    Write-Host "3. Run: buildozer android deploy run" -ForegroundColor White
    Write-Host ""
    Write-Host "Or manually install:" -ForegroundColor Yellow
    Write-Host "   adb install -r bin/khelbhoomi-0.1-debug.apk" -ForegroundColor White
    Write-Host ""
    Write-Host "To monitor camera logs:" -ForegroundColor Yellow
    Write-Host "   adb logcat | Select-String 'python|camera|opencv'" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "❌ BUILD FAILED!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the error messages above." -ForegroundColor Yellow
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "- Missing Android SDK/NDK" -ForegroundColor White
    Write-Host "- Missing Python dependencies" -ForegroundColor White
    Write-Host "- Network issues downloading packages" -ForegroundColor White
    Write-Host ""
    Write-Host "Try running: buildozer android clean" -ForegroundColor White
    Write-Host "Then run this script again." -ForegroundColor White
    Write-Host ""
}
