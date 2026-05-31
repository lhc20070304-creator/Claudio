Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Run desktop.py without console window, don't wait
WshShell.CurrentDirectory = scriptDir
WshShell.Run """" & scriptDir & "\.venv\Scripts\pythonw.exe"" """ & scriptDir & "\desktop.py""", 0, False
