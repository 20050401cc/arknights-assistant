Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "PID=$($_.Id)  CPU=$([math]::Round($_.CPU,1))  MEM=$([math]::Round($_.WorkingSet64/1MB,0))MB"
}
