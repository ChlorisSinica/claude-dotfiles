$ErrorActionPreference = "Continue"

$verifyCommand = @"
python -m pytest --tb=short -q
"@

$logDir = ".agents/logs/verify"
$historyDir = Join-Path $logDir "history"
New-Item -ItemType Directory -Path $historyDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$startedAt = (Get-Date).ToString("o")
$logPath = Join-Path $historyDir "$timestamp-verify.log"
$statusPath = Join-Path $historyDir "$timestamp-status.json"
$latestLog = Join-Path $logDir "latest.log"
$latestStatus = Join-Path $logDir "latest.status.json"

try {
    Invoke-Expression $verifyCommand 2>&1 | Tee-Object -FilePath $logPath
    $exitCode = if ($LASTEXITCODE -ne $null) { [int]$LASTEXITCODE } else { 0 }
} catch {
    $_ | Out-String | Tee-Object -FilePath $logPath -Append | Out-Host
    $exitCode = 1
}

$finishedAt = (Get-Date).ToString("o")
$status = [PSCustomObject]@{
    ok = ($exitCode -eq 0)
    command = $verifyCommand.Trim()
    exit_code = $exitCode
    started_at = $startedAt
    finished_at = $finishedAt
    log_path = $logPath
}

$status | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
Copy-Item -LiteralPath $logPath -Destination $latestLog -Force
Copy-Item -LiteralPath $statusPath -Destination $latestStatus -Force

exit $exitCode