@echo off
setlocal EnableExtensions
chcp 65001 >nul

echo.
echo Sketch Curve Cleaner - Fusion 360 Add-In installer
echo.

REM This installer is stored in the source folder:
REM   SketchCurveCleanerLocalizedAddIn\
REM But it deliberately excludes installer/helper files when copying to Fusion 360.

set "SOURCE_DIR=%~dp0"
if "%SOURCE_DIR:~-1%"=="\" set "SOURCE_DIR=%SOURCE_DIR:~0,-1%"

set "TARGET_ROOT=%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns"
set "TARGET_DIR=%TARGET_ROOT%\SketchCurveCleanerLocalizedAddIn"

for %%I in ("%SOURCE_DIR%") do set "SOURCE_FULL=%%~fI"
for %%I in ("%TARGET_DIR%") do set "TARGET_FULL=%%~fI"

if not exist "%SOURCE_DIR%\SketchCurveCleanerLocalizedAddIn.py" (
    echo ERROR: SketchCurveCleanerLocalizedAddIn.py was not found in:
    echo %SOURCE_DIR%
    echo.
    echo This installer must be run from inside the SketchCurveCleanerLocalizedAddIn folder.
    pause
    exit /b 1
)

if /I "%SOURCE_FULL%"=="%TARGET_FULL%" (
    echo The package is already located in the Fusion 360 AddIns folder.
    echo.
    echo Removing installation helper files from the installed add-in folder:
    echo %TARGET_DIR%
    echo.
    del "%TARGET_DIR%\install_to_fusion360.bat" >nul 2>&1
    del "%TARGET_DIR%\uninstall_from_fusion360.bat" >nul 2>&1
    del "%TARGET_DIR%\INSTALL.md" >nul 2>&1
    echo Done.
    echo.
    pause
    exit /b 0
)

if not exist "%TARGET_ROOT%" (
    echo Creating Fusion 360 AddIns folder:
    echo %TARGET_ROOT%
    mkdir "%TARGET_ROOT%"
)

if exist "%TARGET_DIR%" (
    echo Existing installation found. Removing old version:
    echo %TARGET_DIR%
    rmdir /S /Q "%TARGET_DIR%"
)

echo Copying add-in files only.
echo From: %SOURCE_DIR%
echo To  : %TARGET_DIR%
echo.
echo Installer/helper files will be excluded.
echo.

robocopy "%SOURCE_DIR%" "%TARGET_DIR%" /E ^
 /XF install_to_fusion360.bat uninstall_from_fusion360.bat INSTALL.md README_PACKAGE.md ^
 /XD install .git __pycache__ .vscode .idea

set "ROBOCOPY_EXIT=%ERRORLEVEL%"

REM Robocopy exit codes 0 to 7 are success or non-fatal copy statuses.
if %ROBOCOPY_EXIT% GEQ 8 (
    echo.
    echo ERROR: robocopy failed with exit code %ROBOCOPY_EXIT%.
    pause
    exit /b %ROBOCOPY_EXIT%
)

echo.
echo Done.
echo.
echo Installed add-in path:
echo %TARGET_DIR%
echo.
echo The installer/helper files were not copied to Fusion 360.
echo.
echo Restart Fusion 360, then open:
echo Utilities ^> Scripts and Add-Ins ^> Add-Ins
echo.
echo Run SketchCurveCleanerLocalizedAddIn and enable Run on Startup if desired.
echo.
pause
endlocal
