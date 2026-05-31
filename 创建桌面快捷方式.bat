@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Creating Claudio desktop shortcut...

:: Convert PNG to ICO using PowerShell (Windows 10+ can do this natively)
powershell -ExecutionPolicy Bypass -Command ^
"Add-Type -AssemblyName System.Drawing; ^
$png = [System.Drawing.Image]::FromFile('%~dp0Claudio图标.png'); ^
$ico = '%~dp0Claudio.ico'; ^
$bitmap = New-Object System.Drawing.Bitmap($png); ^
$stream = New-Object System.IO.FileStream($ico, [System.IO.FileMode]::Create); ^
$bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Icon); ^
$stream.Close(); $png.Dispose(); $bitmap.Dispose(); ^
Write-Host 'ICO created'"

:: Create shortcut via VBS (now pointing to ICO, not PNG)
set "VBS=%TEMP%\claudio_shortcut.vbs"
set "TARGET=%~dp0launch.vbs"
set "ICON=%~dp0Claudio.ico"

> "%VBS%" (
    echo Set ws = CreateObject^("WScript.Shell"^)
    echo desktop = ws.SpecialFolders^("Desktop"^)
    echo Set sc = ws.CreateShortcut^(desktop ^& "\Claudio.lnk"^)
    echo sc.TargetPath = "%TARGET%"
    echo sc.WorkingDirectory = "%~dp0"
    echo sc.Description = "Claudio AI Music Radio"
    echo sc.IconLocation = "%ICON%"
    echo sc.WindowStyle = 7
    echo sc.Save
)

cscript //Nologo "%VBS%"
del "%VBS%"

echo Done.
pause
