@echo off
setlocal
chcp 65001 >nul

echo.
echo Sketch Curve Cleaner - Fusion 360 Add-In uninstaller
echo.

set "TARGET_DIR=%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SketchCurveCleanerLocalizedAddIn"

if exist "%TARGET_DIR%" (
    echo Removing installed add-in folder:
    echo %TARGET_DIR%
    rmdir /S /Q "%TARGET_DIR%"
    echo.
    echo Done.
) else (
    echo Add-in folder not found:
    echo %TARGET_DIR%
)

echo.
pause
endlocal
