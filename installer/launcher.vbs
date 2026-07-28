' Sabrina launcher — runs launcher.py (embedded python) hidden, then opens the browser.
Option Explicit
Dim WSH, cmd, py, launcher
Set WSH = CreateObject("WScript.Shell")
py = WSH.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Sabrina\python\python.exe"
launcher = WSH.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Sabrina\installer\launcher.py"
cmd = """" & py & """ """ & launcher & """"
WSH.Run cmd, 0, False
