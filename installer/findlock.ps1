$path = "C:\Users\NateMina\AppData\Local\Sabrina\ollama-windows.zip"
Get-Process | ForEach-Object {
  try {
    $_.Modules | ForEach-Object {
      if ($_.FileName -eq $path) { "$($_.Id) $($_.Name)" }
    }
  } catch {}
}
# also check via handle-equivalent: open files via WMI is heavy; just report defenders
Get-Process MsMpEng -ErrorAction SilentlyContinue | ForEach-Object { "DEFENDER $($_.Id)" }
