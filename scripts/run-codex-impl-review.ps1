param(
    [string]$TaskDescription = "",
    [string[]]$Files = @(),
    [string[]]$IncludeFiles = @(),
    [ValidateRange(30, 7200)]
    [int]$ReviewTimeoutSec = 600,
    [switch]$NoPrevious
)

$ErrorActionPreference = "Stop"
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$Utf8Strict = [System.Text.UTF8Encoding]::new($false, $true)
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom

function Read-Utf8TextStrict {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.File]::ReadAllText($Path, $Utf8Strict)
}

function Write-Utf8Text {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

function Write-ReviewDiagnostics {
    param([AllowNull()][string]$Text)

    if (-not $Text -or -not $Text.Trim()) {
        return
    }

    foreach ($line in ($Text -split "`r?`n")) {
        if ($line.Trim()) {
            [Console]::Error.WriteLine($line.TrimEnd())
        }
    }
}

function Test-IsWindowsHost {
    return [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
}

function Invoke-PluginPromptFixIfAvailable {
    if (-not (Test-IsWindowsHost)) {
        return
    }

    $homeRoot = if ($env:USERPROFILE) {
        $env:USERPROFILE
    }
    elseif ([Environment]::GetFolderPath("UserProfile")) {
        [Environment]::GetFolderPath("UserProfile")
    }
    else {
        $HOME
    }

    $scriptPath = Join-Path $homeRoot ".claude\scripts\fix-codex-plugin-prompts.ps1"
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        return
    }

    try {
        & $scriptPath | Out-Null
    }
    catch {
        Write-ReviewDiagnostics -Text "Plugin prompt fix script failed: $($_.Exception.Message)"
    }
}

function Test-CodexNeedsUnelevatedFallback {
    param([AllowNull()][string]$OutputText)

    if (-not (Test-IsWindowsHost) -or -not $OutputText) {
        return $false
    }

    foreach ($pattern in @(
        'CreateProcessAsUserW failed',
        'windows sandbox: runner error',
        'windows sandbox failed',
        'Windows sandbox setup is missing or out of date',
        'Couldn''t set up your sandbox with Administrator permissions'
    )) {
        if ($OutputText -match [regex]::Escape($pattern)) {
            return $true
        }
    }

    return $false
}

function Join-CommandText {
    param(
        [AllowNull()][string]$StdoutText,
        [AllowNull()][string]$StderrText
    )

    $parts = New-Object System.Collections.Generic.List[string]
    if ($StdoutText -and $StdoutText.Trim()) {
        $null = $parts.Add($StdoutText.TrimEnd())
    }
    if ($StderrText -and $StderrText.Trim()) {
        $null = $parts.Add($StderrText.TrimEnd())
    }
    return ($parts -join "`n")
}

function Write-ReviewAttemptDiagnostics {
    param(
        [AllowNull()][string]$StdoutText,
        [AllowNull()][string]$StderrText,
        [switch]$IncludeStdout
    )

    Write-ReviewDiagnostics -Text $StderrText

    if ($IncludeStdout -and $StdoutText -and $StdoutText.Trim()) {
        Write-ReviewDiagnostics -Text $StdoutText
    }
}

function Stop-ProcessSafely {
    param([Parameter(Mandatory = $true)][System.Diagnostics.Process]$Process)

    if ($Process.HasExited) {
        return
    }

    try {
        $Process.Kill($true)
    }
    catch {
        if (-not $Process.HasExited) {
            try {
                $Process.Kill()
            }
            catch {
                # Ignore cleanup failures and surface the timeout instead.
            }
        }
    }
}

function Get-StrictReviewVerdict {
    param(
        [Parameter(Mandatory = $true)][string]$ReviewText,
        [Parameter(Mandatory = $true)][string[]]$AllowedVerdicts
    )

    foreach ($line in (($ReviewText -split "`r?`n") | Select-Object -Reverse)) {
        $trimmed = $line.Trim()
        if (-not $trimmed) {
            continue
        }

        foreach ($verdict in $AllowedVerdicts) {
            if ($trimmed -ceq "VERDICT: $verdict") {
                return $verdict
            }
        }

        return $null
    }

    return $null
}

function ConvertTo-PowerShellSingleQuotedLiteral {
    param([AllowNull()][string]$Text)

    if ($null -eq $Text) {
        return "''"
    }

    return "'" + ($Text -replace "'", "''") + "'"
}

function Resolve-CodexCommand {
    $command = Get-Command codex -ErrorAction Stop
    while ($command.CommandType.ToString() -eq "Alias") {
        $command = Get-Command $command.Definition -ErrorAction Stop
    }
    return $command
}

function Get-CodexCommandScript {
    param([Parameter(Mandatory = $true)][string[]]$Args)

    $resolved = Resolve-CodexCommand
    $argLiterals = @($Args | ForEach-Object { ConvertTo-PowerShellSingleQuotedLiteral -Text $_ })
    $argsExpression = "@(" + ($argLiterals -join ", ") + ")"
    $scriptLines = New-Object System.Collections.Generic.List[string]

    switch ($resolved.CommandType.ToString()) {
        "Function" {
            $null = $scriptLines.Add("function codex {")
            foreach ($line in ($resolved.ScriptBlock.ToString().TrimEnd() -split "`r?`n")) {
                $null = $scriptLines.Add($line)
            }
            $null = $scriptLines.Add("}")
        }
        "ExternalScript" {
            $target = ConvertTo-PowerShellSingleQuotedLiteral -Text $resolved.Path
            $null = $scriptLines.Add('$script:CodexTarget = ' + $target)
        }
        default {
            if ($resolved.Name -ne "codex" -and ($resolved.Source -or $resolved.Path)) {
                $targetPath = if ($resolved.Source) { $resolved.Source } else { $resolved.Path }
                $target = ConvertTo-PowerShellSingleQuotedLiteral -Text $targetPath
                $null = $scriptLines.Add('$script:CodexTarget = ' + $target)
            }
        }
    }

    $null = $scriptLines.Add('$inputText = [Console]::In.ReadToEnd()')
    $null = $scriptLines.Add('$codexArgs = ' + $argsExpression)
    if ($scriptLines | Where-Object { $_ -like '$script:CodexTarget = *' }) {
        $null = $scriptLines.Add('$inputText | & $script:CodexTarget @codexArgs')
    }
    else {
        $null = $scriptLines.Add('$inputText | & codex @codexArgs')
    }

    return ($scriptLines -join "`n")
}

function Invoke-CodexCommand {
    param(
        [Parameter(Mandatory = $true)][string[]]$Args,
        [Parameter(Mandatory = $true)][string]$InputPath,
        [Parameter(Mandatory = $true)][int]$TimeoutSec
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $shellPath = try {
        (Get-Process -Id $PID -ErrorAction Stop).Path
    }
    catch {
        if (Test-IsWindowsHost) { "pwsh.exe" } else { "pwsh" }
    }
    $psi.FileName = $shellPath
    $psi.WorkingDirectory = (Get-Location).Path
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true

    $null = $psi.ArgumentList.Add("-NoProfile")
    if (Test-IsWindowsHost) {
        $null = $psi.ArgumentList.Add("-ExecutionPolicy")
        $null = $psi.ArgumentList.Add("Bypass")
    }
    $null = $psi.ArgumentList.Add("-Command")
    $null = $psi.ArgumentList.Add((Get-CodexCommandScript -Args $Args))

    try {
        $psi.StandardInputEncoding = $Utf8NoBom
        $psi.StandardOutputEncoding = $Utf8NoBom
        $psi.StandardErrorEncoding = $Utf8NoBom
    }
    catch {
        # Older runtimes may not expose the encoding properties; fall back to defaults.
    }

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $psi

    try {
        if (-not $process.Start()) {
            throw "Failed to start codex process."
        }

        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()

        try {
            $process.StandardInput.Write((Read-Utf8TextStrict -Path $InputPath))
        }
        finally {
            $process.StandardInput.Close()
        }

        $timeoutMs = [int]([Math]::Max($TimeoutSec, 1) * 1000)
        $exited = $process.WaitForExit($timeoutMs)
        if (-not $exited) {
            Stop-ProcessSafely -Process $process
            $null = $process.WaitForExit(5000)
            return @{
                ExitCode = -1
                StdoutText = $stdoutTask.GetAwaiter().GetResult().TrimEnd()
                StderrText = $stderrTask.GetAwaiter().GetResult().TrimEnd()
                TimedOut = $true
            }
        }

        $process.WaitForExit()

        return @{
            ExitCode = $process.ExitCode
            StdoutText = $stdoutTask.GetAwaiter().GetResult().TrimEnd()
            StderrText = $stderrTask.GetAwaiter().GetResult().TrimEnd()
            TimedOut = $false
        }
    }
    finally {
        $process.Dispose()
    }
}

function Invoke-CodexReview {
    param([Parameter(Mandatory = $true)][string]$InputPath)

    Invoke-PluginPromptFixIfAvailable

    $preferUnelevated = (Test-IsWindowsHost) -and ($env:CODEX_REVIEW_FORCE_UNELEVATED -match '^(?i:1|true|yes)$')
    $attempts = @(
        [ordered]@{
            Label = "default"
            Args = @("review", "-")
        }
    )
    if (Test-IsWindowsHost) {
        $unelevatedAttempt = [ordered]@{
            Label = "unelevated"
            Args = @("review", "-c", 'windows.sandbox="unelevated"', "-")
        }

        if ($preferUnelevated) {
            $attempts = @($unelevatedAttempt) + $attempts
        }
        else {
            $attempts += $unelevatedAttempt
        }
    }

    foreach ($attempt in $attempts) {
        $commandResult = Invoke-CodexCommand -Args $attempt.Args -InputPath $InputPath -TimeoutSec $ReviewTimeoutSec
        $stdoutText = [string]$commandResult.StdoutText
        $stderrText = [string]$commandResult.StderrText
        $combinedText = Join-CommandText -StdoutText $stdoutText -StderrText $stderrText
        $exitCode = [int]$commandResult.ExitCode
        $timedOut = [bool]$commandResult.TimedOut

        if ($exitCode -eq 0) {
            Write-ReviewAttemptDiagnostics -StdoutText $stdoutText -StderrText $stderrText
            if ($attempt.Label -eq "unelevated" -and -not $preferUnelevated) {
                Write-ReviewDiagnostics -Text 'Codex elevated Windows sandbox failed; retried with windows.sandbox="unelevated". Re-run the Codex Windows sandbox setup later if you want the stronger sandbox back.'
            }
            return $stdoutText
        }

        if ($timedOut) {
            if ($attempt.Label -eq "default" -and (Test-CodexNeedsUnelevatedFallback -OutputText $combinedText)) {
                Write-ReviewAttemptDiagnostics -StdoutText $stdoutText -StderrText $stderrText -IncludeStdout
                Write-ReviewDiagnostics -Text 'Codex elevated Windows sandbox failed before review completion; retrying with windows.sandbox="unelevated".'
                continue
            }

            Write-ReviewAttemptDiagnostics -StdoutText $stdoutText -StderrText $stderrText -IncludeStdout
            $detail = if ($combinedText) { $combinedText } else { "codex review exceeded the timeout of $ReviewTimeoutSec seconds." }
            throw "codex review timed out after $ReviewTimeoutSec seconds (attempt: $($attempt.Label)).`n$detail"
        }

        if ($attempt.Label -eq "default" -and (Test-CodexNeedsUnelevatedFallback -OutputText $combinedText)) {
            Write-ReviewAttemptDiagnostics -StdoutText $stdoutText -StderrText $stderrText -IncludeStdout
            Write-ReviewDiagnostics -Text 'Codex elevated Windows sandbox failed; retrying with windows.sandbox="unelevated".'
            continue
        }

        $detail = if ($combinedText) { $combinedText } else { "codex review exited with code $exitCode." }
        throw "codex review failed (attempt: $($attempt.Label), exit $exitCode).`n$detail"
    }

    throw "codex review failed after retrying."
}

function Read-SessionsState {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        $state = Read-Utf8TextStrict -Path $Path | ConvertFrom-Json -AsHashtable
        if ($null -eq $state) {
            $state = @{}
        }
    } else {
        $state = @{}
    }

    if (-not $state.ContainsKey('reviews') -or $null -eq $state['reviews']) {
        $state['reviews'] = @()
    }
    if (-not $state.ContainsKey('current') -or $null -eq $state['current']) {
        $state['current'] = @{}
    }
    if (-not $state['current'].ContainsKey('plan_review') -or $null -eq $state['current']['plan_review']) {
        $state['current']['plan_review'] = @{
            phase_a_cycles = 0
            phase_b_cycles = 0
        }
    }
    if (-not $state['current'].ContainsKey('impl_review') -or $null -eq $state['current']['impl_review']) {
        $state['current']['impl_review'] = @{
            cycle = 0
        }
    }
    return $state
}

function Write-SessionsState {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)]$State
    )

    Write-Utf8Text -Path $Path -Content (($State | ConvertTo-Json -Depth 20) -replace "`r?`n", "`n")
}

function Get-TextHash {
    param([Parameter(Mandatory = $true)][string]$Text)

    $bytes = $Utf8NoBom.GetBytes($Text)
    $hashBytes = [System.Security.Cryptography.SHA256]::HashData($bytes)
    return ([System.BitConverter]::ToString($hashBytes) -replace '-', '').ToLowerInvariant()
}

function Append-Section {
    param(
        [Parameter(Mandatory = $true)]$Builder,
        [Parameter(Mandatory = $true)][string]$Title,
        [AllowNull()]$Content
    )

    $text = if ($null -eq $Content) { "" } else { [string]$Content }
    if (-not $text.Trim()) {
        return
    }

    [void]$Builder.AppendLine("---")
    [void]$Builder.AppendLine("# $Title")
    [void]$Builder.AppendLine("")
    [void]$Builder.AppendLine($text.TrimEnd())
    [void]$Builder.AppendLine("")
}

function Get-RepoRelativePath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $combined = if ([System.IO.Path]::IsPathRooted($Path)) { $Path } else { Join-Path (Get-Location).Path $Path }
    $resolved = [System.IO.Path]::GetFullPath($combined)
    $root = [System.IO.Path]::GetFullPath((Get-Location).Path).TrimEnd('\', '/')
    if (-not $resolved.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside repo root: $Path"
    }
    return $resolved.Substring($root.Length).TrimStart('\', '/').Replace('\', '/')
}

function Get-UniquePaths {
    param([string[]]$InputPaths)

    $list = New-Object System.Collections.Generic.List[string]
    foreach ($path in $InputPaths) {
        if (-not $path) {
            continue
        }
        $relative = Get-RepoRelativePath -Path $path
        if (-not $list.Contains($relative)) {
            $null = $list.Add($relative)
        }
    }
    return @($list)
}

function Get-ChangedFiles {
    $output = & git diff --name-only --diff-filter=ACMRTUXB
    if ($LASTEXITCODE -ne 0) {
        throw "git diff --name-only failed."
    }
    return @($output | Where-Object { $_ -and $_.Trim() })
}

$repoRoot = (Get-Location).Path
$agentsDir = Join-Path $repoRoot ".agents"
$contextDir = Join-Path $agentsDir "context"
$reviewsDir = Join-Path $agentsDir "reviews"
$promptsDir = Join-Path $agentsDir "prompts"
$sessionsPath = Join-Path $reviewsDir "sessions.json"

$promptPath = Join-Path $promptsDir "codex_impl_review.md"
$bundlePath = Join-Path $contextDir "_codex_input.tmp"
$contextOutput = Join-Path $contextDir "codex_impl_review.md"
$reviewOutput = Join-Path $reviewsDir "impl-review.md"
$planPath = Join-Path $contextDir "plan.md"
$tasksPath = Join-Path $contextDir "tasks.md"

$sessionsState = Read-SessionsState -Path $sessionsPath
$currentCycle = [int]$sessionsState['current']['impl_review']['cycle'] + 1
$sessionsState['current']['impl_review']['cycle'] = $currentCycle
Write-SessionsState -Path $sessionsPath -State $sessionsState

$targetFiles = if ($Files.Count -gt 0) { Get-UniquePaths -InputPaths $Files } else { Get-UniquePaths -InputPaths (Get-ChangedFiles) }
if ($targetFiles.Count -eq 0) {
    throw "No files to review."
}
$dependencyFiles = Get-UniquePaths -InputPaths $IncludeFiles

$taskSummary = if ($TaskDescription) {
    $TaskDescription
} else {
    "Review changes in " + ($targetFiles -join ", ")
}

$promptContent = Read-Utf8TextStrict -Path $promptPath
$promptContent = $promptContent.Replace('$TASK_DESCRIPTION', $taskSummary)
$promptContent = $promptContent.Replace('$FILE_LIST', ($targetFiles -join ", "))

$builder = New-Object System.Text.StringBuilder
Append-Section -Builder $builder -Title "Prompt" -Content $promptContent
if (Test-Path -LiteralPath $planPath -PathType Leaf) {
    Append-Section -Builder $builder -Title "plan.md" -Content (Read-Utf8TextStrict -Path $planPath)
}
if (Test-Path -LiteralPath $tasksPath -PathType Leaf) {
    Append-Section -Builder $builder -Title "tasks.md" -Content (Read-Utf8TextStrict -Path $tasksPath)
}

$diffOutput = & git diff --no-ext-diff -- @($targetFiles)
if ($LASTEXITCODE -ne 0) {
    throw "git diff failed."
}
Append-Section -Builder $builder -Title "git diff" -Content (($diffOutput | Out-String).TrimEnd())

foreach ($relativePath in $targetFiles) {
    $fullPath = Join-Path $repoRoot ($relativePath -replace '/', '\')
    if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
        try {
            Append-Section -Builder $builder -Title "file: $relativePath" -Content (Read-Utf8TextStrict -Path $fullPath)
        } catch [System.Text.DecoderFallbackException] {
            Append-Section -Builder $builder -Title "file: $relativePath" -Content "[binary or non-UTF8 file omitted]"
        }
    }
}

foreach ($relativePath in $dependencyFiles) {
    $fullPath = Join-Path $repoRoot ($relativePath -replace '/', '\')
    if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
        try {
            Append-Section -Builder $builder -Title "dependency: $relativePath" -Content (Read-Utf8TextStrict -Path $fullPath)
        } catch [System.Text.DecoderFallbackException] {
            Append-Section -Builder $builder -Title "dependency: $relativePath" -Content "[binary or non-UTF8 file omitted]"
        }
    }
}

if ((-not $NoPrevious) -and (Test-Path -LiteralPath $contextOutput -PathType Leaf)) {
    Append-Section -Builder $builder -Title "Previous Review" -Content (Read-Utf8TextStrict -Path $contextOutput)
}

$bundleText = $builder.ToString()
$null = Get-TextHash -Text $bundleText
Write-Utf8Text -Path $bundlePath -Content $bundleText
$reviewText = Invoke-CodexReview -InputPath $bundlePath
if (-not $reviewText) {
    throw "codex review returned empty output."
}
$verdict = Get-StrictReviewVerdict -ReviewText $reviewText -AllowedVerdicts @("APPROVED", "CONDITIONAL", "REVISE")
if (-not $verdict) {
    $reviewText = $reviewText + "`n`nVERDICT: CONDITIONAL"
    $verdict = Get-StrictReviewVerdict -ReviewText $reviewText -AllowedVerdicts @("APPROVED", "CONDITIONAL", "REVISE")
    Write-ReviewDiagnostics -Text "Final non-empty line was not a valid VERDICT. Appended fallback VERDICT: CONDITIONAL."
}
$reviewText = $reviewText.TrimEnd() + "`n"

Write-Utf8Text -Path $contextOutput -Content $reviewText
Write-Utf8Text -Path $reviewOutput -Content $reviewText
if ($verdict -eq "APPROVED") {
    $reviews = @($sessionsState['reviews'])
    $reviews += @{
        kind = "impl-review"
        cycle = $currentCycle
        date = (Get-Date).ToString("o")
        verdict = "APPROVED"
    }
    $sessionsState['reviews'] = $reviews
    $sessionsState['current']['impl_review']['cycle'] = 0
    Write-SessionsState -Path $sessionsPath -State $sessionsState
}
Write-Output "VERDICT: $verdict"
Write-Output "Cycle: $currentCycle"
Write-Output "Bundle: $bundlePath"
Write-Output "Review: $contextOutput"
Write-Output "Sessions: $sessionsPath"
